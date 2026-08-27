import os

import fastapi
import numpy as np
import requests
from fastapi import FastAPI, Response
from tensorflow import keras
from random import shuffle

import mlflow

import secrets
import zipfile
import io

from model import ClassifierModel
import share_tools

app = FastAPI()
OWN_MLFLOW = os.environ["mlflow_tracking_uri_internal"]


@app.on_event("startup")
def on_startup():
    app.model = ClassifierModel()
    print("model created")
    mlflow.set_tracking_uri(OWN_MLFLOW)


@app.api_route("/health", methods=["GET", "HEAD"], status_code=fastapi.status.HTTP_200_OK)
async def health_check():
    pass


async def download_training_data(uri: str, local_path: str) -> None:
    response = requests.get(uri, stream=True)
    with open(local_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)


@app.post("/train_model")
async def do_training(train_config: dict) -> dict:
    '''
        Doing a local model update.
        Parameters:
            - train_config:
                {"global_model_host": "http://..." # <- download global model from here,
                 "global_model_id": "m-132456412" # <- ID of the global model (MLFlow artifact URI),
                 "global_model_user": "client" # <- username for downloading the global model (if needed),
                 "global_model_password": "..." # <- password for downloading the global model (if needed
                 "train_data_uri": "./train_data" # <- path or uri to train data,
                 "forward_model_to": ["http://aggregator1:8000", "http://aggregator2:8000"] # <- where to forward the model shares
                 "epochs": 10 # <- number of epochs to train the model
                 "batch_size": 64 # <- batch size for training
                }
        Returns:
            - a dictionary, containing the shares' URIs and the number of training samples used for the local model update
                
    '''
    assert len(train_config["forward_model_to"])%2 == 0 or len(train_config["forward_model_to"]) == 1, "forward_model_to must contain an even number of endpoints"

    if "global_model_id" in train_config and train_config["global_model_id"] != "":
        print("loading global model")
        if "global_model_user" in train_config and "global_model_password" in train_config:
            os.environ["MLFLOW_TRACKING_USERNAME"] = train_config["global_model_user"]
            os.environ["MLFLOW_TRACKING_PASSWORD"] = train_config["global_model_password"]
        mlflow.set_tracking_uri(train_config["global_model_host"])
        app.model.neural_network = mlflow.tensorflow.load_model(train_config["global_model_id"])
        if "global_model_user" in train_config and "global_model_password" in train_config:
            del os.environ["MLFLOW_TRACKING_USERNAME"]
            del os.environ["MLFLOW_TRACKING_PASSWORD"]
        mlflow.set_tracking_uri(OWN_MLFLOW)

    print("training")
    if train_config["train_data_uri"].startswith("http"):
        await download_training_data(train_config["train_data_uri"], "/train_data.npz")
        train_config["train_data_uri"] = "/train_data.npz"
    train_data = np.load(train_config["train_data_uri"])
    x_train = train_data["x_train"]
    y_train = train_data["y_train"]
    early_stopping = keras.callbacks.EarlyStopping(monitor='loss',
                                                   patience=5)
    app.model.neural_network.fit(x_train, y_train,
                                 batch_size=train_config.get("batch_size", 64),
                                 shuffle=True,
                                 epochs=train_config.get("epochs", 10),
                                 callbacks=[early_stopping])

    print("training finished, forwarding model shares")

    if len(train_config["forward_model_to"]) != 1:
        shares = share_tools.create_shares(app.model.neural_network, len(train_config["forward_model_to"]))
    else:
        shares = [app.model.neural_network]

    shuffle(shares)

    model_ids = []
    for share, forward_to in zip(shares, train_config["forward_model_to"]):
        model_id = secrets.token_hex(32)
        model_path = f"/tmp/{model_id}"
        os.makedirs(model_path, exist_ok=True)
        share.save(model_path)
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
        model_ids.append(model_id)
    return {
        "n_samples": len(x_train),
        "model_ids": model_ids
    }
