import asyncio
import io
import json
import os
import secrets

import zipfile
import numpy as np
import requests
import tensorflow as tf
import keras

import agg_algorithms
import shutil

async def _store_reputations(reputations: dict[str | float], lock_name: str):
    while os.path.exists(lock_name):
        print("waiting for lock")
        await asyncio.sleep(np.random.randint(10) / 100)
    with open("reputations.json", "w") as f:
        json.dump(reputations, f)
    try:
        os.remove(lock_name)
    except OSError:
        pass
    return True


async def _load_reputations(lock_name: str) -> dict[str | float]:
    while os.path.exists(lock_name):
        print("waiting for lock")
        await asyncio.sleep(np.random.randint(10) / 100)
    try:
        with open("reputations.json", "r") as f:
            reputations = json.load(f)
    except FileNotFoundError:
        reputations = {}
    try:
        os.remove(lock_name)
    except OSError:
        pass
    return reputations

async def load_model(model_uri: str, lock_name: str):
    while os.path.exists(lock_name):
        print("waiting for lock")
        await asyncio.sleep(np.random.randint(10) / 100)
    with open(f"{model_uri}/model.json", "r") as f:
        model_data = json.load(f)
    model = keras.models.model_from_json(json.dumps(model_data))
    model.load_weights(f"{model_uri}/model.weights.h5")
    try:
        os.remove(lock_name)
    except OSError:
        pass
    return model

async def store_model(model_id: str,
                      model_data: dict,
                      model_path: str,
                      lock_name: str):
    while os.path.exists(lock_name):
        print("waiting for lock")
        await asyncio.sleep(np.random.randint(10) / 100)
    os.makedirs(f"{model_path}/{model_id}", exist_ok=True)
    with open(f"{model_path}/{model_id}/model.zip", "wb") as f:
        f.write(model_data)
    shutil.unpack_archive(f"{model_path}/{model_id}/model.zip", f"{model_path}/{model_id}")
    try:
        os.remove(lock_name)
    except OSError:
        pass
    return True


async def aggregate_models(aggregation_config: dict,
                           lock_name: str,
                           model_path: str,
                           test_data_path: str = ""):
    print("Aggregation: gathering local models")
    
    models = {}
    deltarep_n_samples = {}
    reputations = await _load_reputations(lock_name)
    if reputations == {}:
        reputations["contribution"] = {host: 0.0 for host in aggregation_config["model_sources"]}
        reputations["participation"] = {host: 0 for host in aggregation_config["model_sources"]}

    for source, model_id in zip(aggregation_config["model_sources"],
                                    aggregation_config["model_ids"]):
        print(f"loading model from {source}; model: {model_id}")
        models[source] = await load_model(f"{model_path}/{model_id}", lock_name)
        deltarep_n_samples[source] = aggregation_config["local_data_sizes"][
            aggregation_config["model_sources"].index(source)]
        reputations["participation"][source] += 1

    print("fedavg calculation started"
          if aggregation_config["aggregation_algorithm"] == "fedavg"
          else "deltarep calculation started"
    )

    print("models: ", models)

    if aggregation_config["aggregation_algorithm"] == "fedavg":
        combined_model = agg_algorithms.fed_avg(models, aggregation_config["local_data_sizes"])
    else:
        train_data = np.load(test_data_path)
        x_test = train_data["x_test"]
        y_test = train_data["y_test"]
        global_model = await load_model(aggregation_config["global_model_id"], lock_name)
        combined_model, reps = agg_algorithms.delta_rep(
            models,
            global_model,
            x_test, y_test,
            deltarep_n_samples,
            reputations["participation"],
            reputations["contribution"],
        )
        reputations["contribution"] = reps

    await _store_reputations(reputations, lock_name)

    return combined_model

async def forward_model(combined_model: keras.Model,
                        forward_to: str,
                        lock_name: str):
    while os.path.exists(lock_name):
        print("waiting for lock")
        await asyncio.sleep(np.random.randint(10) / 100)
    model_id = secrets.token_hex(32)
    model_path = f"/tmp/{model_id}"
    os.makedirs(model_path, exist_ok=True)
    model_structure = combined_model.neural_network.to_json()
    with open(f"{model_path}/model.json", "w") as f:
        json.dump(json.loads(model_structure), f)
    combined_model.neural_network.save_weights(f"{model_path}/model.weights.h5", overwrite=True)
    shutil.make_archive("model", "zip", model_path)
    with open("model.zip", "rb") as f:
        model_data = f.read()

    print(f"Forwarding aggregated model {model_id} to {forward_to}")
    response = requests.post(
        f"{forward_to}/post_model",
        params={"model_id": model_id},
        data=model_data
    )
    if response.status_code != 200:
        raise Exception(f"Failed to forward model to {forward_to}: {response.text}")
    try:
        os.remove(lock_name)
    except OSError:
        pass
    return model_id
