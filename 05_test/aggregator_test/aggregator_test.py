import os
import requests
import json
import numpy as np
import tensorflow as tf
from tensorflow import keras
import mlflow
import pytest

def create_dummy_model(input_shape):
    model = keras.Sequential([
        keras.layers.InputLayer(shape=input_shape),
        keras.layers.Flatten(),
        keras.layers.Dense(128, activation='relu'),
        keras.layers.Dense(10, activation='softmax')
    ])
    return model


def mlflow_log_client_model(client_id):
    weights_path = f"05_test/aggregator_test/dummy_models/client_{client_id}.weights.h5"
    input_shape = os.environ.get("MLFLOW_INPUT_SHAPE", (28, 28))
    model = create_dummy_model(input_shape=input_shape)
    model.load_weights(weights_path)
    model.compile(optimizer='adam',
                  loss='sparse_categorical_crossentropy',
                  metrics=['accuracy'])
    with mlflow.start_run(run_name=f"client_{client_id}_run") as run:
        # Log the model to MLflow
        mlflow.tensorflow.log_model(model, f"client_{client_id}_model")
        return run.info.run_id

def mlflow_load_client_model(as_user, experiment_name, mlflow_client_number):
    as_user("admin")
    mlflow.set_experiment(experiment_name)
    for client_id in range(mlflow_client_number):
        mlflow_log_client_model(client_id)

def get_run_ids(experiment_name):
    experiment = mlflow.get_experiment_by_name(experiment_name)
    runs_df = mlflow.search_runs([experiment.experiment_id])
    run_ids = runs_df["run_id"].tolist()
    run_ids.reverse()
    return run_ids

def pull_all_models(as_user, experiment_name):
    as_user("admin")
    mlflow.set_experiment(experiment_name)
    experiment = mlflow.get_experiment_by_name(experiment_name)
    models = mlflow.search_logged_models(
        experiment_ids=[experiment.experiment_id],
        order_by=[{"field_name": "creation_time", "ascending": False}],
        output_format="list"
    )
    return models

def pull_test_data():
    x_test = np.load("02_data/mnist/test_images.npy")
    y_test = np.load("02_data/mnist/test_labels.npy")
    return x_test, y_test


def test_fedavg_aggregation(aggregator_container, as_user, experiment_name, mlflow_client_number):
    mlflow_load_client_model(as_user, experiment_name, mlflow_client_number)
    run_ids = get_run_ids(experiment_name)
    aggregation_config = {
        "local_model_hosts": [
            "http://localhost:5000"
            for _ in range(mlflow_client_number)
        ],
        "local_model_uris": [
            f"runs:/{run_ids[client_id]}/client_{client_id}_model"
            for client_id in range(mlflow_client_number)
        ],
        "local_data_size": [
            len(np.load(f"02_data/mnist/client_data/client_{client_id}_train_images.npy"))
            for client_id in range(mlflow_client_number)
        ],
        "aggregation_algorithm": "fedavg",
        
    }
    response = requests.post("http://localhost:9100/aggregate_models", json=aggregation_config)
    assert response.status_code == 200

def test_pull_fedavg_model(aggregator_container, as_user, experiment_name):
    models = pull_all_models(as_user, experiment_name)
    latest_model = models[0]
    aggregated_model = mlflow.tensorflow.load_model(f"models:/{latest_model.model_id}")
    aggregated_model.compile(
        optimizer="adam",
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    assert aggregated_model is not None
    client_models = []
    for client_model in models[1:]:
        client_model = mlflow.tensorflow.load_model(f"models:/{client_model.model_id}")
        client_model.compile(
            optimizer="adam",
            loss="sparse_categorical_crossentropy",
            metrics=["accuracy"],
        )
        assert client_model is not None
        client_models.append(client_model)

    x_test, y_test = pull_test_data()
    aggregated_loss, aggregated_accuracy = aggregated_model.evaluate(x_test, y_test, verbose=0)
    client_accuracies = [client_model.evaluate(x_test, y_test, verbose=0)[1] for client_model in client_models]
    min_client_accuracy = np.min(client_accuracies)
    client_losses = [client_model.evaluate(x_test, y_test, verbose=0)[0] for client_model in client_models]
    max_client_loss = np.max(client_losses)
    assert aggregated_accuracy >= min_client_accuracy, f"Aggregated model accuracy {aggregated_accuracy} is better than minimum client accuracy {min_client_accuracy}"
    assert aggregated_loss <= max_client_loss, f"Aggregated model loss {aggregated_loss} is less than maximum client loss {max_client_loss}"