import numpy as np

import requests
import json
import os

from fastapi import FastAPI, Response


import tensorflow as tf
from tensorflow import keras
import mlflow

from model import ClassifierModel

OWN_MLFLOW = os.environ["mlflow_tracking_uri_internal"]
app = FastAPI()

@app.api_route("/health", methods=["GET", "HEAD"])
async def health_check():
    status_code = requests.get(f"{OWN_MLFLOW}/health").status_code
    return Response(status_code=status_code)
    
    
    
def fed_avg(models: list[keras.Sequential],
            n_samples: list[int])->keras.Sequential:
    '''
        Computes the FedAvg aggregation.
        Parameters:
            - models: list of models
            - n_samples: list of number of training samples
        Returns:
            - the FedAvg'd model
    '''
    avg_model = ClassifierModel()
    total_samples = np.sum(n_samples)
    
    for li in range(len(avg_model.neural_network.layers)):
        weights = []
        for mi in range(len(models)):
            if len(weights)==0:
                for w in models[mi].layers[li].get_weights():
                    weights.append(n_samples[mi]/total_samples*w)
            else:
                for i, w in enumerate(models[mi].layers[li].get_weights()):
                    weights[i] += n_samples[mi]/total_samples*w

        avg_model.neural_network.layers[li].set_weights(
            weights
        )
        
    return avg_model
        

@app.post("/aggregate_models")
async def do_aggregation(aggregation_config: dict) -> dict:
    '''
        Doing a local model update.
        Parameters:
            - aggregation_config:
                {"local_model_hosts": ["http://...", ...] # <- download local models from this list,
                 "local_model_uris": "ag1_1" # <- MLFlow ids of the shared models
                }
        Returns:
            - dict: {aggregated_model_host, aggregated_model_uri}
                
    '''
    print("Aggregation: gathering local models")
    models = []
    for local_uri, model_id in zip(aggregation_config["local_model_hosts"],
                                   aggregation_config["local_model_uris"]):
        print(f"loading model from {local_uri}; model: {model_id}")
        mlflow.set_tracking_uri(local_uri)
        models.append(
            mlflow.tensorflow.load_model(model_id)
        )

    print("fedavg calculation started")
    combined_model = fed_avg(models, aggregation_config["local_data_size"])
    print("storing avg'd model")
    mlflow.set_tracking_uri(OWN_MLFLOW)
    mlflow.set_experiment("default")
    model_info = mlflow.tensorflow.log_model(combined_model.neural_network)
        
    return {
        "aggregated_model_host_external": os.environ["mlflow_tracking_uri_external"],
        "aggregated_model_host_organizational": os.environ["mlflow_tracking_uri_organizational"],
        "aggregated_model_uri": f"{model_info.model_uri}"
    }

