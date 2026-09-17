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

def mlflow_load_model(model_name):
    response = requests.get(f"http://localhost:8555/{model_name}.weights.h5")
    response.raise_for_status()
    weights_path = f"{model_name}.weights.h5"
    with open(weights_path, "wb") as f:
        f.write(response.content)
    input_shape = os.environ.get("MLFLOW_INPUT_SHAPE", (28, 28))
    model = create_dummy_model(input_shape=input_shape)
    model.load_weights(weights_path)
    model.compile(optimizer='adam',
                    loss='sparse_categorical_crossentropy',
                    metrics=['accuracy'])
    with mlflow.start_run(run_name=f"{model_name}_run") as run:
        # Log the model to MLflow
        mlflow.tensorflow.log_model(model, f"{model_name}_model")
        return run.info.run_id

def get_run_ids(experiment_name):
    experiment = mlflow.get_experiment_by_name(experiment_name)
    runs_df = mlflow.search_runs([experiment.experiment_id])
    run_ids = runs_df["run_id"].tolist()
    run_ids.reverse()
    return run_ids

def pull_test_data():
    x_test_binary = requests.get("http://localhost:8555/test-data/test_images.npy")
    x_test_binary.raise_for_status()
    y_test_binary = requests.get("http://localhost:8555/test-data/test_labels.npy")
    y_test_binary.raise_for_status()
    with open("02_data/mnist/test_images.npy", "wb") as f:
        f.write(x_test_binary.content)
    with open("02_data/mnist/test_labels.npy", "wb") as f:
        f.write(y_test_binary.content)
    x_test = np.load("02_data/mnist/test_images.npy", allow_pickle=True)
    y_test = np.load("02_data/mnist/test_labels.npy", allow_pickle=True)
    return x_test, y_test

def test_aggregation_success(aggregator_container, as_user, experiment_name, mlflow_client_number):
    as_user("admin")
    mlflow.set_experiment(experiment_name)
    mlflow_load_model("aggregated")
    for client_id in range(mlflow_client_number):
            mlflow_load_model(f"client_{client_id}")
    run_ids = get_run_ids(experiment_name)
    for client_id in range(mlflow_client_number):
            x_train_binary = requests.get(f"http://localhost:8555/client_data/client_{client_id}_train_images.npy")
            with open(f"02_data/mnist/client_data/client_{client_id}_train_images.npy", "wb") as f:
                f.write(x_train_binary.content)
    client_ids = run_ids[1:]
    aggregation_config = {
        "local_model_hosts": [
            "http://localhost:5000"
            for _ in range(mlflow_client_number)
        ],
        "local_model_uris": [
            f"runs:/{client_ids[client_id]}/client_{client_id}_model"
            for client_id in range(mlflow_client_number)
        ],
        "local_data_size": [
            len(np.load(f"02_data/mnist/client_data/client_{client_id}_train_images.npy"))
            for client_id in range(mlflow_client_number)
        ],
        "aggregation_algorithm": "deltarep",
        "global_model_host": "http://localhost:5000",
        "global_model_uri": f"runs:/{run_ids[0]}/aggregated_model"            
    }
    response = requests.post("http://localhost:9100/aggregate_models", json=aggregation_config)
    assert response.status_code == 200