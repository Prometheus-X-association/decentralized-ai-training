import tensorflow as tf
from tensorflow import keras

from threading import Lock

class ClassifierModel:
    def __init__(self):
        self.__lock = Lock()
        self.neural_network = keras.Sequential(
            [
                keras.layers.Flatten(input_shape=(28,28)),
                keras.layers.Dense(128, activation='relu'),
                keras.layers.Dense(10, activation='softmax')
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
