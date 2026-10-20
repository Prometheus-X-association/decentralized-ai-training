import os
import json

import mlflow
import fastapi
import requests
import asyncio
import numpy as np
from fastapi import FastAPI, Response, APIRouter
from mlflow.server import get_app_client

import agg_helper

LOCK_NAME = ".edge_fl_lock"
TEST_DATA_PATH = "/data/course_test.npz"

MLFLOW_USER_INFO = ".mlflow_user_info"
MLFLOW_ADMIN_CONFIG_PATH = "/cfg/mlflow_admin.json"
MLFLOW_EXPERIMENT_NAME = "edge-fl-experiment"
OWN_MLFLOW = os.environ["MLFLOW_TRACKING_URI_INTERNAL"]

MODELS_PATH = os.getenv("MODELS_PATH", "models")

app = FastAPI(title="Top-level Aggregator")


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

@router.post("/post_model")
async def post_model(request: fastapi.Request) -> dict:
    model_id = request.query_params["model_id"]
    model_data = await request.body()
    print(f"Received model {model_id} of size {len(model_data)} bytes")
    successful_storage = await agg_helper.store_model(model_id, model_data, MODELS_PATH, LOCK_NAME)
    if not successful_storage:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
                                    detail=f"Failed to store model {model_id}")
    return {"message": f"Model {model_id} stored successfully"}


@router.post("/aggregate_models")
async def do_aggregation(aggregation_config: dict) -> dict:
    '''
        Doing a local model update.
        Parameters:
            - aggregation_config:
                {"model_sources": ["client1", "client2", ...], # <- producers of the local models to aggregate
                    "model_ids": ["model_1", "model_2", ...], # <- ids of the local models to aggregate
                    "local_data_sizes": [100, 200, ...] # <- number of training samples used for each local model (only for fedavg)
                    "aggregation_algorithm": "fedavg" # <- which aggregation algorithm to use (fedavg, deltarep)
                    "global_model_id": "glob_0" # <- MLFlow id of the global model (only for deltarep),
                    "forward_model_to": "http://top_aggregator:8000",# <- where to forward the aggregated model
                }
        Returns:
            - dict: {aggregated_model_host, aggregated_model_uri}
                
    '''
    combined_model, reputations = await agg_helper.aggregate_models(aggregation_config,
                                                       LOCK_NAME,
                                                       MODELS_PATH,
                                                       TEST_DATA_PATH)

    print("storing agg'd model")
    if "MLFLOW_BASIC_AUTH" in os.environ:
        with open(MLFLOW_USER_INFO, "r") as f:
            mlflow_user_info = json.load(f)
        os.environ["MLFLOW_TRACKING_USERNAME"] = "aggregator"
        os.environ["MLFLOW_TRACKING_PASSWORD"] = mlflow_user_info["aggregator_password"]
    mlflow.set_tracking_uri(OWN_MLFLOW)
    if "MLFLOW_BASIC_AUTH" in os.environ:
        mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)
    model_info = mlflow.keras.log_model(combined_model.neural_network)

    answer = {
        "aggregated_model_host_external": os.environ["mlflow_tracking_uri_external"],
        "aggregated_model_host_organizational": os.environ["mlflow_tracking_uri_organizational"],
        "aggregated_model_uri": f"{model_info.model_uri}",
    }

    if "MLFLOW_BASIC_AUTH" in os.environ:
        answer["aggregated_model_username"] = "model_user"
        answer["aggregated_model_password"] = mlflow_user_info["model_user_password"]

    if aggregation_config["aggregation_algorithm"] == "deltarep":
        answer["reputations_scores"] = reputations

    return answer


########################################################################################################################

app.include_router(router=router)
