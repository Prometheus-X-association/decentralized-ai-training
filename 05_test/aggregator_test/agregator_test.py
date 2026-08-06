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
        keras.layers.Flatten(input_shape=input_shape),
        keras.layers.Dense(128, activation='relu'),
        keras.layers.Dense(10, activation='softmax')
    ])
    model.compile(optimizer='adam',
                  loss='sparse_categorical_crossentropy',
                  metrics=['accuracy'])
    return model

def train_client(client_id):
    # Load client data
    x_train = np.load(f"{DATA_PATH}/client_data/client_{client_id}_train_images.npy")
    y_train = np.load(f"{DATA_PATH}/client_data/client_{client_id}_train_labels.npy")
    # Create and train the model
    model = create_dummy_model(input_shape=x_train.shape[1:])
    model.fit(x_train, y_train, epochs=3)
    # Save the trained model weights
    model.save_weights(f"dummy_models/client_{client_id}.weights.h5")

def mlflow_log_client_model(client_id):
    weights_path = f"dummy_models/client_{client_id}.weights.h5"
    x_train = np.load(f"{DATA_PATH}/client_data/client_{client_id}_train_images.npy")
    input_shape = x_train.shape[1:]
    model = create_dummy_model(input_shape=input_shape)
    model.load_weights(weights_path)
    model.compile(optimizer='adam',
                  loss='sparse_categorical_crossentropy',
                  metrics=['accuracy'])
    with mlflow.start_run(run_name=f"client_{client_id}_run") as run:
        # Log the model to MLflow
        mlflow.tensorflow.log_model(model, f"client_{client_id}_model")
        return run.info.run_id
