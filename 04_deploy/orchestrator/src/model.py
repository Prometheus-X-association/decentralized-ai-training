from threading import Lock

import tensorflow as tf
from tensorflow import keras


class ClassifierModel:
    def __init__(self):
        self.__lock = Lock()
        self.neural_network = keras.Sequential(
            [
                keras.Input([28, 28, 1]),
                keras.layers.Conv2D(8, 2),
                keras.layers.MaxPool2D(2),
                keras.layers.Flatten(),
                keras.layers.Dense(10, activation="softmax"),
                keras.layers.Dense(1, activation="relu")
            ]
        )
        self.neural_network.compile(
            optimizer=keras.optimizers.Adam(learning_rate=1e-3),
            loss=keras.losses.MSE
        )

    def load_model(self, model_json: dict):
        # TODO!
        with self.__lock:
            pass

    def train(self, path: str):
        # TODO!
        with self.__lock:
            pass
        return True

    def serialize_model(self):
        return keras.models.model_to_json(self.neural_network)
