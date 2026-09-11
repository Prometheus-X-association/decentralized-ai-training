import asyncio
import json
import os
import secrets

import fastapi
import mlflow
import numpy as np
import requests
import tensorflow as tf
from fastapi import FastAPI, Response, APIRouter
from mlflow.server import get_app_client
from tensorflow import keras

import agg_algorithms

LOCK_NAME = ".edge_fl_lock"
TEST_DATA_PATH = "/data/course_test.npz"

MLFLOW_USER_INFO = ".mlflow_user_info"
MLFLOW_ADMIN_CONFIG_PATH = "/cfg/mlflow_admin.json"

MLFLOW_EXPERIMENT_NAME = "edge-fl-experiment"


async def _store_reputations(reputations: dict[str | float]):
    while os.path.exists(LOCK_NAME):
        print("waiting for lock")
        await asyncio.sleep(np.random.randint(10) / 100)
    with open("reputations.json", "w") as f:
        json.dump(reputations, f)
    try:
        os.remove(LOCK_NAME)
    except OSError:
        pass
    return True


async def _load_reputations() -> dict[str | float]:
    while os.path.exists(LOCK_NAME):
        print("waiting for lock")
        await asyncio.sleep(np.random.randint(10) / 100)
    try:
        with open("reputations.json", "r") as f:
            reputations = json.load(f)
    except FileNotFoundError:
        reputations = {}
    try:
        os.remove(LOCK_NAME)
    except OSError:
        pass
    return reputations


OWN_MLFLOW = os.environ["mlflow_tracking_uri_internal"]

app = FastAPI(title="Orchestrator")


@app.on_event("startup")
async def startup_event():
    app.reputations = None
    app.participation_counts = None
    print("checking MLFlow configuration")

    if "MLFLOW_BASIC_AUTH" in os.environ:
        # regardless the number of workers, setting up MLFlow credentials only once:
        if not (os.path.exists(MLFLOW_USER_INFO)):
            print("MLFlow user info not found, configuring MLFlow server")
            # signaling others of MLFlow is being configured:
            with open(MLFLOW_USER_INFO, "w") as f:
                f.write("lock")
            # waiting for MLFlow server to be up and running:
            status_code = 0
            while status_code != 200:
                try:
                    status_code = requests.get(f"{OWN_MLFLOW}/health").status_code
                except requests.exceptions.ConnectionError:
                    print("MLFlow server not available yet, retrying...")
                    status_code = 0
                if status_code != 200:
                    await asyncio.sleep(1)

            # configuring MLFlow credentials:
            # admin configuration:
            MLFLOW_ADMIN_CONFIG_PATH = os.path.join(os.getcwd(), "cfg", "mlflow_admin.json")
            with open(MLFLOW_ADMIN_CONFIG_PATH, "r") as f:
                admin_config = json.load(f)
            # creating an MLFlow experiment:
            print("configuring MLFlow server")
            os.environ["MLFLOW_TRACKING_USERNAME"] = "admin"
            os.environ["MLFLOW_TRACKING_PASSWORD"] = admin_config["admin_password"]
            mlflow.set_tracking_uri(OWN_MLFLOW)
            experiment_id = mlflow.create_experiment(MLFLOW_EXPERIMENT_NAME)

            # client = get_app_client("basic-auth", OWN_MLFLOW)
            # client.update_user_password(
            #     username="admin",
            #     password=admin_config["admin_password"]
            # )
            # os.environ["MLFLOW_TRACKING_PASSWORD"] = admin_config["admin_password"]

            # user configuration:
            client = get_app_client("basic-auth", OWN_MLFLOW)
            aggregator_password = admin_config["aggregator_password"]#secrets.token_urlsafe(32)
            #print(f"Aggregator password: {aggregator_password}")
            client.create_user(username="aggregator", password=aggregator_password)
            client.grant_user_permission(
                username="aggregator",
                resource_type="experiment",
                resource_id=experiment_id,
                permission="MANAGE"
            )
            client_password = admin_config["model_user_password"]#secrets.token_urlsafe(32)
            client.create_user(username="model_user", password=client_password)
            #print(f"Model user password: {client_password}")
            client.grant_user_permission(
                username="model_user",
                resource_type="experiment",
                resource_id=experiment_id,
                permission="USE"
            )

            with open(MLFLOW_USER_INFO, "w") as f:
                json.dump({
                    "experiment_id": experiment_id,
                    "aggregator_password": aggregator_password,
                    "model_user_password": client_password
                }, f)
        else:
            print("MLFlow already configured, skipping setup")


@app.api_route("/health", methods=["GET", "HEAD"])
async def health_check():
    try:
        status_code = requests.get(f"{OWN_MLFLOW}/health").status_code
        return Response(status_code=status_code)
    except requests.exceptions.RequestException:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_503_SERVICE_UNAVAILABLE)


########################################################################################################################

STATIC_PREFIX_API = os.getenv("STATIC_PREFIX_API", "")
router = APIRouter(prefix=os.getenv("STATIC_PREFIX_API", ""))


@router.post("/aggregate_models")
async def do_aggregation(aggregation_config: dict) -> dict:
    '''
        Doing a local model update.
        Parameters:
            - aggregation_config:
                {"local_model_hosts": ["http://...", ...] # <- download local models from this list,
                 "local_model_uris": "ag1_1" # <- MLFlow ids of the shared models
                 "local_data_size": [100, 200, ...] # <- number of training samples used for each local model (only for fedavg)
                 "aggregation_algorithm": "fedavg" # <- which aggregation algorithm to use (fedavg, deltarep)
                 "global_model_host": "http://..." # <- download global model from this host (only for deltarep)
                 "global_model_uri": "orch_0" # <- MLFlow id of the global model (only for deltarep)
                }
        Returns:
            - dict: {aggregated_model_host, aggregated_model_uri}
                
    '''
    print("Aggregation: gathering local models")
    client_ids = [f"client_{i}" for i in range(len(aggregation_config["local_model_hosts"]))]
    models = {}
    deltarep_n_samples = {}
    reputations = await _load_reputations()
    if reputations == {}:
        reputations["contribution"] = {host: 0.0 for host in client_ids}
        reputations["participation"] = {host: 0 for host in client_ids}

    if "MLFLOW_BASIC_AUTH" in os.environ:
            with open(MLFLOW_USER_INFO, "r") as f:
                mlflow_user_info = json.load(f)
            os.environ["MLFLOW_TRACKING_USERNAME"] = "aggregator"
            os.environ["MLFLOW_TRACKING_PASSWORD"] = mlflow_user_info["aggregator_password"]

    for client_id, local_host, model_id, data_size in zip(client_ids,
                                                          aggregation_config["local_model_hosts"],
                                                          aggregation_config["local_model_uris"],
                                                          aggregation_config["local_data_size"]):
        print(f"loading model from {local_host}; model: {model_id}")
        mlflow.set_tracking_uri(local_host)
        models[client_id] = mlflow.tensorflow.load_model(model_id)
        deltarep_n_samples[client_id] = data_size
        reputations["participation"][client_id] += 1

    print("fedavg calculation started" if aggregation_config[
                                              "aggregation_algorithm"] == "fedavg" else "deltarep calculation started")

    if aggregation_config["aggregation_algorithm"] == "fedavg":
        combined_model = agg_algorithms.fed_avg(models, aggregation_config["local_data_size"])
    else:
        train_data = np.load(TEST_DATA_PATH)
        x_test = train_data["x_test"]
        y_test = train_data["y_test"]
        mlflow.set_tracking_uri(aggregation_config["global_model_host"])
        global_model = mlflow.tensorflow.load_model(aggregation_config["global_model_uri"])
        combined_model, reps = agg_algorithms.delta_rep(
            models,
            global_model,
            x_test, y_test,
            deltarep_n_samples,
            reputations["participation"],
            reputations["contribution"],
        )
        reputations["contribution"] = reps

    print("storing agg'd model")
    
    mlflow.set_tracking_uri(OWN_MLFLOW)
    if "MLFLOW_BASIC_AUTH" in os.environ:
        mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)
    model_info = mlflow.tensorflow.log_model(combined_model.neural_network)
    await _store_reputations(reputations)

    answer = {
        "aggregated_model_host_external": os.environ["mlflow_tracking_uri_external"],
        "aggregated_model_host_organizational": os.environ["mlflow_tracking_uri_organizational"],
        "aggregated_model_uri": f"{model_info.model_uri}",
    }

    if "MLFLOW_BASIC_AUTH" in os.environ:
        answer["aggregated_model_username"] = "model_user"
        answer["aggregated_model_password"] = mlflow_user_info["model_user_password"]

    if aggregation_config["aggregation_algorithm"] == "deltarep":
        answer["reputations_scores"] = reputations["contribution"]

    return answer


########################################################################################################################

app.include_router(router=router)
