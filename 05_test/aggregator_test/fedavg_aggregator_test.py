import os
import requests
import numpy as np
import tensorflow as tf
from tensorflow import keras
import mlflow
import pytest

from agg_test_helpers import create_dummy_model, get_model_ids, post_model_to_aggregator, pull_test_data, pull_train_data, get_agg_config

def test_fedavg_aggregation(aggregator_container, mlflow_client_number, data_path):
    for client_id in range(mlflow_client_number):
        post_model_to_aggregator(f"dummy_models/client_{client_id}", f"client_{client_id}", f"model_{client_id}", model_to_upload=None)
    pull_train_data(mlflow_client_number)
    aggregation_config = get_agg_config(mlflow_client_number, data_path, "fedavg")
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