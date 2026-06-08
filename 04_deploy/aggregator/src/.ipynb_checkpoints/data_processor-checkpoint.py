import requests
import json
import os
import datetime

import mlflow

from fastapi import FastAPI

from model import ClassifierModel

app = FastAPI()

@app.on_event("startup")
def on_startup():
    app.model = ClassifierModel()
    print("model created")
    mlflow.set_tracking_uri(os.environ["mlflow_tracking_uri"])
        

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


    if "global_model_uri" in train_config:
        print("loading global model")
        global_uri = train_config["global_model_uri"]
        gmodel_response = await requests.get(f"{global_uri}/get_model")
        app.model.neural_network = await app.model.load_model(gmodel_response.json())

    print("training")
    app.model.train(path = train_config["train_data_uri"])
    mlflow.set_experiment("default")
    model_info = mlflow.tensorflow.log_model(
        app.model.neural_network,
        name = train_config["local_model_id"]
    )
    
    
    return {
        "model_server_uri": os.environ["mlflow_tracking_uri"],
        "model_share_id": f"{model_info.model_uri}"
    }


@app.get("/get_model")
async def get_model(model_uri: str) -> dict:
    now = datetime.datetime.now().timestamp()
    model_file_path = f".model{now}.weights.json"
    model = ClassifierModel()
    print("loading model from MLFLow")
    model.neural_network = mlflow.tensorflow.load_model(model_uri)
    
    print("model loaded, serializing")
    model.neural_network.save_weights(model_file_path, max_shard_size=0.25)
    with open(model_file_path) as f:
        model_dict = json.load(f)
    os.remove(model_file_path)
    return model_dict
    #return app.model.serialize_model()