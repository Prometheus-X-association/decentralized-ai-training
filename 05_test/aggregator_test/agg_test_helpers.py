import shutil
import json
import os
import requests
import numpy as np
import tensorflow as tf
from tensorflow import keras
import mlflow

def create_dummy_model(input_shape):
    model = keras.Sequential([
        keras.layers.InputLayer(shape=input_shape),
        keras.layers.Flatten(),
        keras.layers.Dense(128, activation='relu'),
        keras.layers.Dense(10, activation='softmax')
    ])
    return model


def get_model_ids(experiment_name):
    experiment = mlflow.get_experiment_by_name(experiment_name)
    models = mlflow.search_logged_models(
        experiment_ids=[experiment.experiment_id],
        order_by=[{"field_name": "creation_time", "ascending": False}],
        output_format="list"
    )
    model_ids = [model.model_id for model in models]
    return model_ids

def pull_train_data(number_of_clients):
    for client_id in range(number_of_clients):
        x_train_binary = requests.get(f"http://localhost:8555/client_data/client_{client_id}_train_images.npy")
        with open(f"02_data/mnist/client_data/client_{client_id}_train_images.npy", "wb") as f:
            f.write(x_train_binary.content)
        y_train_binary = requests.get(f"http://localhost:8555/client_data/client_{client_id}_train_labels.npy")
        with open(f"02_data/mnist/client_data/client_{client_id}_train_labels.npy", "wb") as f:
            f.write(y_train_binary.content)

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

    np.savez(
        "02_data/agg_test/mnist_test.npz",
        x_test=x_test,
        y_test=y_test,
    )
    return x_test, y_test

def post_model_to_aggregator(model_path, model_name, model_id, model_to_upload):
    os.makedirs(model_path, exist_ok=True)
    weights_path = f"{model_path}/model.weights.h5"
    if model_to_upload is None:
        # 1. Download the model weights from the Fured cloud storage
        response = requests.get(f"http://localhost:8555/{model_name}.weights.h5")
        response.raise_for_status()  # raises an exception on 4xx/5xx instead of silently continuing
        # 2. Save the weights to a local file
        with open(weights_path, "wb") as f:
                f.write(response.content)
        print(f"Model {response.content} weights downloaded.")
    else:
        # Alternative path, save locally available model
        model_to_upload.save_weights(weights_path)

    # 3. Reconstruct the model architecture and load the weights
    input_shape = os.environ.get("MLFLOW_INPUT_SHAPE", (28, 28))
    model = create_dummy_model(input_shape=input_shape)
    model.load_weights(weights_path)
    model.compile(optimizer='adam',
                    loss='sparse_categorical_crossentropy',
                    metrics=['accuracy'])
    # 4. Save the model structure to a JSON file
    model_structure = model.to_json()
    with open(f"{model_path}/model.json", "w") as json_file:
        json.dump(json.loads(model_structure), json_file)
    # 5. Create a zip which contains both the model structure and the weights
    shutil.make_archive("model", "zip", model_path)
    with open("model.zip", "rb") as f:
        model_data = f.read()
    # 6. Post the model zip to the aggregator
    response = requests.post(
        f"http://localhost:9100/post_model",
        params={"model_id": model_id},
        data=model_data
    )
    if response.status_code != 200:
        raise Exception(f"Failed to forward model to aggregator: {response.text}")

def get_agg_config(mlflow_client_number, data_path, agg_aglorithm):
    return {
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
        "global_model_id": "models/global_model",
        "aggregation_algorithm": agg_aglorithm,
        "forward_model_to": "http://top_aggregator:8000",
}