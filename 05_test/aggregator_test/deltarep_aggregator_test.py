import os
import requests
import json
import numpy as np
import tensorflow as tf
from tensorflow import keras
import mlflow
import pytest

from attack import AttackManager, AttackSpec
from agg_test_helpers import create_dummy_model, get_run_ids, get_model_ids, pull_test_data

client_reputations = {}

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


def retrain_clients_on_new_aggregate(loop_cycle, model_id, attack_manager, mlflow_client_number):
    for client_id in range(mlflow_client_number):
        # Load the new aggregated model weights into the client model
        client_model = mlflow.tensorflow.load_model(f"models:/{model_id}")
        weights_before_training = [
            weights.copy()
            for weights in client_model.get_weights()
        ]
        if loop_cycle == 1:
            x_train_binary = requests.get(f"http://localhost:8555/client_data/client_{client_id}_train_images.npy")
            with open(f"02_data/mnist/client_data/client_{client_id}_train_images.npy", "wb") as f:
                f.write(x_train_binary.content)
            y_train_binary = requests.get(f"http://localhost:8555/client_data/client_{client_id}_train_labels.npy")
            with open(f"02_data/mnist/client_data/client_{client_id}_train_labels.npy", "wb") as f:
                f.write(y_train_binary.content)
        x_train = np.load(f"02_data/mnist/client_data/client_{client_id}_train_images.npy", allow_pickle=True)
        y_train = np.load(f"02_data/mnist/client_data/client_{client_id}_train_labels.npy", allow_pickle=True)
        client_model.compile(optimizer='adam',
                             loss='sparse_categorical_crossentropy',
                             metrics=['accuracy'])
        client_model.fit(x_train, y_train, epochs=3)
        delta = [after - before
                 for after, before in zip(client_model.get_weights(), weights_before_training)
        ]
        delta, attack_type = attack_manager.apply(client_id, delta, loop_cycle)
        final_weights = [before + d for before, d in zip(weights_before_training, delta)]
        client_model.set_weights(final_weights)
        with mlflow.start_run(run_name=f"client_{client_id}_run_{loop_cycle}") as run:
                # Log the model to MLflow
                mlflow.tensorflow.log_model(client_model, f"client_{client_id}_model_{loop_cycle}")

        #client_model.save_weights(f"dummy_models/cycle{loop_cycle}/client_{client_id}.weights.h5")  

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
    reputations = response.json()["reputations_scores"]
    for client_id in range(mlflow_client_number):
        client_name = f"client_{client_id}"
        client_reputations[client_name] = [reputations[client_name]]
    assert response.status_code == 200

def test_pull_deltarep_model(aggregator_container, as_user, experiment_name):
    as_user("admin")
    experiment = mlflow.get_experiment_by_name(experiment_name)
    prev_agg_id = get_run_ids(experiment_name)[0]
    models = mlflow.search_logged_models(
        experiment_ids=[experiment.experiment_id],
        order_by=[{"field_name": "creation_time", "ascending": False}],
        output_format="list"
    )
    new_aggregated = models[0]
    new_aggregated_model = mlflow.tensorflow.load_model(f"models:/{new_aggregated.model_id}")
    new_aggregated_model.compile(
        optimizer="adam",
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    run_name = f"runs:/{prev_agg_id}/aggregated_model"
    previous_aggregated_model = mlflow.tensorflow.load_model(run_name)
    previous_aggregated_model.compile(
        optimizer="adam",
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )

    x_test, y_test = pull_test_data()
    new_aggregated_loss, new_aggregated_accuracy = new_aggregated_model.evaluate(x_test, y_test, verbose=0)
    previous_aggregated_loss, previous_aggregated_accuracy = previous_aggregated_model.evaluate(x_test, y_test, verbose=0)
    assert new_aggregated_loss <= previous_aggregated_loss

def test_reputation_scores(aggregator_container, as_user, experiment_name, mlflow_client_number):
    as_user("admin")
    attack_manager = AttackManager({
        0: AttackSpec("none"),
        1: AttackSpec("none"),
        2: AttackSpec("sign_flip")
    })
    for loop_cycle in range(1, 4):
        last_agg_model_id = get_model_ids(experiment_name)[-1]
        # prev_agg_id = get_run_ids(experiment_name)[-1]
        retrain_clients_on_new_aggregate(loop_cycle, last_agg_model_id, attack_manager, mlflow_client_number=3)
        clients_ids = get_run_ids(experiment_name)[-3:]
        global_model_id = get_model_ids(experiment_name)[-4]
        aggregation_config = {
                "local_model_hosts": [
                    "http://localhost:5000"
                    for _ in range(mlflow_client_number)
                ],
                "local_model_uris": [
                    f"runs:/{clients_ids[client_id]}/client_{client_id}_model_{loop_cycle}"
                    for client_id in range(mlflow_client_number)
                ],
                "local_data_size": [
                    len(np.load(f"02_data/mnist/client_data/client_{client_id}_train_images.npy"))
                    for client_id in range(mlflow_client_number)
                ],
                "aggregation_algorithm": "deltarep",
                "global_model_host": "http://localhost:5000",
                "global_model_uri": f"models:/{global_model_id}"            
        }
        response = requests.post("http://localhost:9100/aggregate_models", json=aggregation_config)
        assert response.status_code == 200
        reputations = response.json()["reputations_scores"]
        for client_id in range(mlflow_client_number):
            client_reputations[f"client_{client_id}"].append(
                reputations[f"client_{client_id}"]
            )

    attack_manager = AttackManager({
            0: AttackSpec("none"),
            1: AttackSpec("random_noise"),
            2: AttackSpec("none")
    })
    for loop_cycle in range(4, 7):
        last_agg_model_id = get_model_ids(experiment_name)[-1]
        # prev_agg_id = get_run_ids(experiment_name)[-1]
        retrain_clients_on_new_aggregate(loop_cycle, last_agg_model_id, attack_manager, mlflow_client_number=3)
        clients_ids = get_run_ids(experiment_name)[-3:]
        global_model_id = get_model_ids(experiment_name)[-4]
        aggregation_config = {
                "local_model_hosts": [
                    "http://localhost:5000"
                    for _ in range(mlflow_client_number)
                ],
                "local_model_uris": [
                    f"runs:/{clients_ids[client_id]}/client_{client_id}_model_{loop_cycle}"
                    for client_id in range(mlflow_client_number)
                ],
                "local_data_size": [
                    len(np.load(f"02_data/mnist/client_data/client_{client_id}_train_images.npy"))
                    for client_id in range(mlflow_client_number)
                ],
                "aggregation_algorithm": "deltarep",
                "global_model_host": "http://localhost:5000",
                "global_model_uri": f"models:/{global_model_id}"            
        }
        response = requests.post("http://localhost:9100/aggregate_models", json=aggregation_config)
        assert response.status_code == 200
        reputations = response.json()["reputations_scores"]
        for client_id in range(mlflow_client_number):
            client_reputations[f"client_{client_id}"].append(
                reputations[f"client_{client_id}"]
            )

        # new approach:  argmin client reputations in the attack interval
        min_reputation_cycle_client_1 = np.argmin(client_reputations["client_1"])
        min_reputation_cycle_client_2 = np.argmin(client_reputations["client_2"])
        assert min_reputation_cycle_client_1 in range(4, 7)
        assert min_reputation_cycle_client_2 in range(1, 4)