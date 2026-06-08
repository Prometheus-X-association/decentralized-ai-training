from threading import Lock

import tensorflow as tf
from tensorflow import keras


class ClassifierModel:
    def __init__(self):
        self.__lock = Lock()
        self.neural_network = keras.Sequential(
            [
                keras.Input(shape=(3,)),
                keras.layers.Dense(32, activation="relu"),
                keras.layers.Dense(16, activation="relu"),
                keras.layers.Dense(1, activation="sigmoid")
            ]
        )
        self.neural_network.compile(
            optimizer="adam",
            loss="binary_crossentropy",
            metrics=["accuracy"]
        )

    def set_model(self, model: keras.Sequential):
        with self.__lock:
            self.neural_network = model

    def serialize_model(self):
        return keras.models.model_to_json(self.neural_network)
