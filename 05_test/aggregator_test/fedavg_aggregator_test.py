import os
import requests
import numpy as np
import tensorflow as tf
from tensorflow import keras
import mlflow
import pytest

from agg_test_helpers import create_dummy_model, get_model_ids, post_client_models_to_aggregator, pull_test_data, pull_train_data

def test_fedavg_aggregation(aggregator_container, mlflow_client_number, data_path):
    post_client_models_to_aggregator(mlflow_client_number)
    pull_train_data(mlflow_client_number)
    aggregation_config = {
        "model_sources": [
            f"client_{client_id}" for client_id in range(mlflow_client_number)
        ],
        "model_ids": [
            f"model_{client_id}" for client_id in range(mlflow_client_number)
        ],
        "local_data_sizes": [
            len(np.load(f"{data_path}/mnist/client_data/client_{client_id}_train_images.npy"))
            for client_id in range(mlflow_client_number)
        ],
        "aggregation_algorithm": "fedavg",
        "forward_model_to": "http://top_aggregator:8000",
    }
    response = requests.post("http://localhost:9100/aggregate_models", json=aggregation_config)
    assert response.status_code == 200

def test_pull_fedavg_model(aggregator_container, as_user, experiment_name, mlflow_client_number):
    as_user("admin")
    mlflow.set_experiment(experiment_name)
    model_ids = get_model_ids(experiment_name)
    latest_model_id = model_ids[0]
    aggregated_model = mlflow.keras.load_model(f"models:/{latest_model_id}")
    aggregated_model.compile(
        optimizer="adam",
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    assert aggregated_model is not None

    client_models = []
    x_test, y_test = pull_test_data()
    for client_id in range(mlflow_client_number):
        # Load the client model
        client_model = create_dummy_model(input_shape=x_test.shape[1:])
        client_model.load_weights(f"dummy_models/client_{client_id}/model.weights.h5")
        client_model.compile(
            optimizer="adam",
            loss="sparse_categorical_crossentropy",
            metrics=["accuracy"],
        )
        client_models.append(client_model)

    aggregated_loss, aggregated_accuracy = aggregated_model.evaluate(x_test, y_test, verbose=0)
    client_losses = [client_model.evaluate(x_test, y_test, verbose=0)[0] for client_model in client_models]
    max_client_loss = np.max(client_losses)
    assert aggregated_loss <= max_client_loss, f"Aggregated model loss {aggregated_loss} is less than maximum client loss {max_client_loss}"