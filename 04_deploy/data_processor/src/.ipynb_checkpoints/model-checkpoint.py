import tensorflow as tf
from tensorflow import keras

from threading import Lock

class ClassifierModel:
    def __init__(self):
        self.__lock = Lock()
        self.neural_network = keras.Sequential(
            [
                keras.Input([28, 28, 3]),
                keras.layers.Conv2D(8, 2),
                keras.layers.MaxPool2D(2),
                keras.layers.Flatten(),
                keras.layers.Dense(2),
                keras.layers.Softmax(),
            ]
        )
        
    def load_model(self, model_json: dict):
        #TODO!
        with self.__lock:
            pass
    
    def train(self, path: str):
        #TODO!
        with self.__lock:
            pass
        return True
    
    def serialize_model(self):
        return keras.models.model_to_json(self.neural_network)
