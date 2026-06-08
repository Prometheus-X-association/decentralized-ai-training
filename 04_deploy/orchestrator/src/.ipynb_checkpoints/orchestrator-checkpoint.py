import requests
import json
import numpy as np

from typing import Annotated
from fastapi import FastAPI, Response, Body
from multiprocessing.pool import ThreadPool

import os
import time

import asyncio

app = FastAPI()

LOCK_NAME = ".edge_fl_lock"

@app.api_route("/health", methods=["GET", "HEAD"])
async def health_check():
    return Response(status_code=200)
    

@app.get("/get_model")
async def get_model() -> dict:
    try:
        global_model = await _load_global_model()
        answer = {
            "model_host": global_model["model_host_external"],
            "model_uri": global_model["model_uri"]
        }
    except Exception as e:
        print(e)
        answer = {}
   
    return answer

@app.get("/get_model_organizational")
async def get_model_org() -> dict:
    try:
        global_model = await _load_global_model()
        answer = {
            "model_host": global_model["model_host_organizational"],
            "model_uri": global_model["model_uri"]
        }
    except Exception as e:
        print(e)
        answer = {}

    return answer

async def _store_global_model(model_path):
    while os.path.exists(LOCK_NAME):
        print("waiting for lock")
        await asyncio.sleep(np.random.randint(10)/100)
    with open(LOCK_NAME, "wb") as lock:
        with open("model.json", "w") as json_file:
            json.dump(model_path, json_file)
    try:
        os.remove(LOCK_NAME)
    except:
        pass
    return True
    
async def _load_global_model():
    print("checking for global model")
    while os.path.exists(LOCK_NAME):
        print("waiting for lock")
        await asyncio.sleep(np.random.randint(10)/10)
    with open(LOCK_NAME, "wb") as lock:
        try:
            with open("model.json") as json_file:
                mod_dict = json.load(json_file)
        except:
            mod_dict = {}
    try:
        os.remove(LOCK_NAME)
    except:
        pass
    return mod_dict

@app.put("/set_global_model")
async def set_global_model(model_path: dict):
    '''
        Sets the global model (URIs).
        Parameters:
            - model_path: a dictionary, describing host's URI (model_host)
                          and the model's URI (model_uri)
    '''
    await _store_global_model(model_path)
    

def post_train_request(parameters: dict)->dict:
    share = requests.post(
        f"{parameters["dp_uri"]}/train_model",
        json = parameters
    )
    return share.json()


@app.post("/start_training")
async def do_training(aggregation_tree: Annotated[
        dict,
        Body(
            examples=[
                {
                    "processors": ["http://dp1:8000", "http://dp2:8000"],
                    "aggregators": ["http://aggregator:8000"],
                    "train_data_uri": ["data/train_data.npz", "data/train_data.npz"]
                }
            ],
        ),
    ]) -> dict:
    print(aggregation_tree)
    
    #Train client models:    
    global_model_host, global_model_uri = "", ""
    try:
        global_model = await _load_global_model()
        global_model_host = global_model["model_host_organizational"]
        global_model_uri = global_model["model_uri"]
    except:
        print("no global model found")
    
    params = []
    for i, proc in enumerate(aggregation_tree["processors"]):
        params.append({
            "dp_uri": proc,
            "global_model_host": global_model_host,
            "global_model_uri": global_model_uri,
            "local_model_id": f"dp_{i}",
            "train_data_uri": aggregation_tree["train_data_uri"][i],
            "num_shares": 1,
        })
        
    with ThreadPool(processes=2) as pool:
        shares = pool.map(post_train_request, params)
    print(shares)
    
    #Aggregating results:
    aggregation_config = {
        "local_model_hosts": [],
        "local_model_uris": [],
        "local_data_size": []
    }
    for sh in shares:
        aggregation_config["local_model_hosts"].append(sh["model_server_host"])
        aggregation_config["local_model_uris"].append(sh["model_share_uri"])
        aggregation_config["local_data_size"].append(sh["n_samples"])
        
    aggregates = requests.post(f"{aggregation_tree['aggregators'][0]}/aggregate_models", json = aggregation_config)
    aggregates = aggregates.json()
    
    print(aggregates)    
    model_dict = {
        "model_host_external": aggregates["aggregated_model_host_external"],
        "model_host_organizational": aggregates["aggregated_model_host_organizational"],
        "model_uri": aggregates["aggregated_model_uri"]
    }
    await _store_global_model(model_dict)
    
    answer = {
        "aggregated_model_host": model_dict["model_host_external"],
        "aggregated_model_uri": model_dict["model_uri"]
    }
    return answer
