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

def get_run_ids(experiment_name):
    experiment = mlflow.get_experiment_by_name(experiment_name)
    runs_df = mlflow.search_runs([experiment.experiment_id])
    run_ids = runs_df["run_id"].tolist()
    run_ids.reverse()
    return run_ids

def get_model_ids(experiment_name):
    experiment = mlflow.get_experiment_by_name(experiment_name)
    models = mlflow.search_logged_models(
        experiment_ids=[experiment.experiment_id],
        order_by=[{"field_name": "creation_time", "ascending": False}],
        output_format="list"
    )
    model_ids = [model.model_id for model in models]
    return model_ids

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