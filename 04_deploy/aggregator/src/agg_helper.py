import asyncio
import io
import json
import os
import secrets

import zipfile
import numpy as np
import requests
import tensorflow as tf
from tensorflow import keras

import agg_algorithms

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
    model = tf.keras.models.load_model(model_uri)
    try:
        os.remove(lock_name)
    except OSError:
        pass
    return model

async def store_model(model_id: str,
                      model_data_zip: bytes,
                      model_path: str,
                      lock_name: str):
    while os.path.exists(lock_name):
        print("waiting for lock")
        await asyncio.sleep(np.random.randint(10) / 100)
    os.makedirs(f"{model_path}/{model_id}", exist_ok=True)
    zip_obj = zipfile.ZipFile(io.BytesIO(model_data_zip))
    zip_obj.extractall(f"{model_path}/{model_id}")
    try:
        os.remove(lock_name)
    except OSError:
        pass
    return True


async def aggregate_models(aggregation_config: dict,
                           lock_name: str,
                           test_data_path: str = ""):
    print("Aggregation: gathering local models")
    
    models = {}
    deltarep_n_samples = {}
    reputations = await _load_reputations()
    if reputations == {}:
        reputations["contribution"] = {host: 0.0 for host in aggregation_config["model_sources"]}
        reputations["participation"] = {host: 0 for host in aggregation_config["model_sources"]}

    for source, model_id in zip(aggregation_config["model_sources"],
                                    aggregation_config["model_ids"]):
        print(f"loading model from {source}; model: {model_id}")
        models[source] = await load_model(model_id, lock_name)
        deltarep_n_samples[source] = aggregation_config["local_data_sizes"][
            aggregation_config["model_sources"].index(source)]
        reputations["participation"][source] += 1

    print("fedavg calculation started"
          if aggregation_config["aggregation_algorithm"] == "fedavg"
          else "deltarep calculation started"
    )

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

async def forward_model(combined_model: tf.keras.Model,
                        forward_to: str,
                        lock_name: str):
    while os.path.exists(lock_name):
        print("waiting for lock")
        await asyncio.sleep(np.random.randint(10) / 100)
    model_id = secrets.token_hex(32)
    model_path = f"/tmp/{model_id}"
    os.makedirs(model_path, exist_ok=True)
    combined_model.save(model_path)
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for root, _, files in os.walk(model_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, model_path)
                zip_file.write(file_path, arcname)
    zip_buffer.seek(0)
    response = requests.post(
        f"{forward_to}/post_model",
        params={"model_id": model_id},
        data=zip_buffer.getvalue(),
        headers={"Content-Type": "application/zip"}
    )
    if response.status_code != 200:
        raise Exception(f"Failed to forward model to {forward_to}: {response.text}")
    try:
        os.remove(lock_name)
    except OSError:
        pass
    return model_id
