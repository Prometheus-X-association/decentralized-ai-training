import requests
import json
import os
import datetime

import mlflow
import numpy as np

from tensorflow import keras

from fastapi import FastAPI, Response

from model import ClassifierModel

app = FastAPI()
OWN_MLFLOW = os.environ["mlflow_tracking_uri_internal"]

@app.on_event("startup")
def on_startup():
    app.model = ClassifierModel()
    print("model created")
    mlflow.set_tracking_uri(OWN_MLFLOW)
    
@app.api_route("/health", methods=["GET", "HEAD"])
async def health_check():
    status_code = requests.get(f"{OWN_MLFLOW}/health").status_code
    return Response(status_code=status_code)
    
        

@app.post("/train_model")
async def do_training(train_config: dict) -> dict:
    '''
        Doing a local model update.
        Parameters:
            - train_config:
                {"global_model_uri": "http://..." # <- download global model from here,
                 "local_model_id": "dp1_1" # <- id of the resulting local model,
                 "train_data_uri": "./train_data" # <- path or uri to train data,
                 "num_shares": 1 # <- how many 'shares' shall be generated
                }
        Returns:
            - a dictionary, containing the shares' URIs
                
    '''


    if "global_model_uri" in train_config and train_config["global_model_uri"] != "":
        print("loading global model")
        mlflow.set_tracking_uri(train_config["global_model_host"])
        app.model.neural_network = mlflow.tensorflow.load_model(train_config["global_model_uri"])
        mlflow.set_tracking_uri(OWN_MLFLOW)

    print("training")
    train_data = np.load(train_config["train_data_uri"])
    x_train = train_data["x_train"]
    y_train = train_data["y_train"]
    early_stopping = keras.callbacks.EarlyStopping(monitor='loss',
                                                   patience=5)
    app.model.neural_network.fit(x_train, y_train,
                                 batch_size=64, shuffle=True,
                                 epochs=10,
                                 callbacks=[early_stopping])
    
    model_info = mlflow.tensorflow.log_model(
        app.model.neural_network,
        name = train_config["local_model_id"]
    )
    
    
    return {
        "model_server_host": os.environ["mlflow_tracking_uri_organizational"],
        "model_share_uri": f"{model_info.model_uri}",
        "n_samples": len(x_train)
    }
