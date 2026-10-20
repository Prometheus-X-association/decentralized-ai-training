import os
import requests
import json
import numpy as np
import tensorflow as tf
from tensorflow import keras
import mlflow
import pytest

from attack import AttackManager, AttackSpec
from agg_test_helpers import create_dummy_model, get_model_ids, post_model_to_aggregator, pull_test_data, pull_train_data, get_agg_config

client_reputations = {}

def retrain_clients_on_new_aggregate(loop_cycle, new_model_id, attack_manager, mlflow_client_number):
    print("Retraining clients on new aggregated model...")
    for client_id in range(mlflow_client_number):
        # Load the new aggregated model weights into the client model
        print(f"Load the new aggregated model weights into the client model {client_id}")
        new_client_model = mlflow.keras.load_model(f"models:/{new_model_id}")
        new_client_model.compile(
            optimizer="adam",
            loss="sparse_categorical_crossentropy",
            metrics=["accuracy"],
        )
        weights_before_training = [
            weights.copy()
            for weights in new_client_model.get_weights()
        ]
        x_train = np.load(f"02_data/mnist/client_data/client_{client_id}_train_images.npy", allow_pickle=True)
        y_train = np.load(f"02_data/mnist/client_data/client_{client_id}_train_labels.npy", allow_pickle=True)
        print("Data loaded")
        new_client_model.compile(optimizer='adam',
                             loss='sparse_categorical_crossentropy',
                             metrics=['accuracy'])
        new_client_model.fit(x_train, y_train, epochs=3)
        delta = [after - before
                 for after, before in zip(new_client_model.get_weights(), weights_before_training)
        ]
        delta, attack_type = attack_manager.apply(client_id, delta, loop_cycle)
        final_weights = [before + d for before, d in zip(weights_before_training, delta)]
        new_client_model.set_weights(final_weights)
        print(f"Final weights for client {client_id} initialized with attack also.")

        new_client_model.save_weights(f"dummy_models/client_{client_id}.weights.h5")
        print(f"Uploading client {client_id} model to aggregator...")
        post_model_to_aggregator(f"dummy_models/{client_id}", f"client_{client_id}", 
                                         f"model_{client_id}", model_to_upload=new_client_model)

def rerun_deltarep_aggregation(loop_cycle, mlflow_client_number, data_path, attack_manager, experiment_name):
    new_model_id = get_model_ids(experiment_name)[0]  # Get the most recent model ID
    retrain_clients_on_new_aggregate(loop_cycle, new_model_id, attack_manager, mlflow_client_number)
    aggregation_config = get_agg_config(mlflow_client_number, data_path, "deltarep")
    response = requests.post("http://localhost:9100/aggregate_models", json=aggregation_config)
    response.raise_for_status()
    reputations = response.json()["reputations_scores"]
    client_reputations["client_0"].append(reputations["client_0"])
    client_reputations["client_1"].append(reputations["client_1"])
    client_reputations["client_2"].append(reputations["client_2"])
    # Downloading the new aggregate model from the aggregator mlfow
    model_ids = get_model_ids(experiment_name)
    new_model_id = model_ids[0]  # Get the most recent model ID
    aggregated_model = mlflow.keras.load_model(f"models:/{new_model_id}")
    aggregated_model.compile(
        optimizer="adam",
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    post_model_to_aggregator(f"dummy_models/global_model", f"aggregated", f"global_model", aggregated_model)

def test_aggregation_success(aggregator_container, as_user, experiment_name, mlflow_client_number, data_path):
    as_user("admin")
    mlflow.set_experiment(experiment_name)
    post_model_to_aggregator(f"dummy_models/global_model", f"aggregated", f"global_model", model_to_upload=None)
    for client_id in range(mlflow_client_number):
        post_model_to_aggregator(f"dummy_models/client_{client_id}", f"client_{client_id}", f"model_{client_id}", model_to_upload=None)
    for client_id in range(mlflow_client_number):
        x_train_binary = requests.get(f"http://localhost:8555/client_data/client_{client_id}_train_images.npy")
        with open(f"02_data/mnist/client_data/client_{client_id}_train_images.npy", "wb") as f:
            f.write(x_train_binary.content)

    pull_train_data(mlflow_client_number)
    x_test, y_test = pull_test_data()
    aggregation_config = get_agg_config(mlflow_client_number, data_path, "deltarep")
    response = requests.post("http://localhost:9100/aggregate_models", json=aggregation_config)
    assert response.status_code == 200, (
         f"Aggregation failed with status code {response.status_code}: {response.text}"
    )
    reputations = response.json()["reputations_scores"]
    for client_id in range(mlflow_client_number):
        client_name = f"client_{client_id}"
        client_reputations[client_name] = [reputations[client_name]]

def test_pull_deltarep_model(aggregator_container, as_user, experiment_name, data_path):
    as_user("admin")
    experiment = mlflow.get_experiment_by_name(experiment_name)
    # Loading previous global model from local storage
    with open("dummy_models/global_model/model.json", "r") as json_file:
        model_structure = json.load(json_file)
    global_model = keras.models.model_from_json(json.dumps(model_structure))
    global_model.load_weights("dummy_models/global_model/model.weights.h5")
    global_model.compile(optimizer='adam',
                    loss='sparse_categorical_crossentropy',
                    metrics=['accuracy'])
    # Downloading the new aggregate model from the aggregator mlfow
    model_ids = get_model_ids(experiment_name)
    new_model_id = model_ids[0]  # Get the most recent model ID
    aggregated_model = mlflow.keras.load_model(f"models:/{new_model_id}")
    aggregated_model.compile(
        optimizer="adam",
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )

    x_test = np.load(data_path / "mnist" / "test_images.npy", allow_pickle=True)
    y_test = np.load(data_path / "mnist" / "test_labels.npy", allow_pickle=True)
    prev_loss, prev_accuracy = global_model.evaluate(x_test, y_test, verbose=0)
    new_loss, new_accuracy = aggregated_model.evaluate(x_test, y_test, verbose=0)
    assert new_loss <= prev_loss
    post_model_to_aggregator(f"dummy_models/global_model", f"aggregated", f"global_model", aggregated_model)

def test_reputation_scores(aggregator_container, as_user, experiment_name, mlflow_client_number, data_path):
    as_user("admin")
    attack_manager = AttackManager({
        0: AttackSpec("none"),
        1: AttackSpec("none"),
        2: AttackSpec("sign_flip")
    })
    for loop_cycle in range(1, 3):
        rerun_deltarep_aggregation(loop_cycle, mlflow_client_number, data_path, attack_manager, experiment_name)

    attack_manager = AttackManager({
            0: AttackSpec("none"),
            1: AttackSpec("random_noise"),
            2: AttackSpec("none")
    })
    for loop_cycle in range(3, 5):
        rerun_deltarep_aggregation(loop_cycle, mlflow_client_number, data_path, attack_manager, experiment_name)

    # new approach:  argmin client reputations in the attack interval
    min_reputation_cycle_client_1 = np.argmin(client_reputations["client_1"])
    min_reputation_cycle_client_2 = np.argmin(client_reputations["client_2"])
    assert min_reputation_cycle_client_1 in range(3, 5)
    assert min_reputation_cycle_client_2 in range(1, 3)