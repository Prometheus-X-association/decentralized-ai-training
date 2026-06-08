import asyncio
import enum
import json
import logging
import os
import pathlib
import shutil
import tempfile
from multiprocessing.pool import ThreadPool
from typing import Annotated

import asyncer
import fastapi
import mlflow
import numpy as np
import requests
from fastapi import FastAPI, Body, Response, APIRouter

log = logging.getLogger(__name__)

LOCK_NAME = os.getenv("LOCK_NAME", ".edge_fl_lock")
ROOT_PATH = os.getenv("ROOT_PATH", "/")

app = FastAPI(title="BB-01 - Orchestrator API", version="0.1.0", root_path=ROOT_PATH)


@app.api_route("/health", methods=["GET", "HEAD"], status_code=fastapi.status.HTTP_200_OK)
async def health_check():
    pass


########################################################################################################################

STATIC_PREFIX_API = os.getenv("STATIC_PREFIX_API", "")
router = APIRouter(prefix=STATIC_PREFIX_API)


@router.get("/get_model")
async def get_model() -> dict:
    try:
        global_model = await _load_global_model()
        answer = {
            "model_host": global_model["model_host_external"],
            "model_uri": global_model["model_uri"],
            # "model_username": os.environ["BASIC_AUTH_USERNAME"],
            # "model_password": os.environ["BASIC_AUTH_PASSWORD"]
        }
    except Exception as e:
        print(e)
        answer = {}

    return answer


class ArchiveExtension(enum.StrEnum):
    zip = "zip"
    tar = "tar"
    gztar = "gzip"
    bztar = "bzip2"


DEF_AGG_URL = f"http://aggregator:5000/{'worker/aggregator' if ROOT_PATH != "/" else ''}"


@router.get("/download_model")
async def download_model(model_uri: str, aggregator: str = DEF_AGG_URL,
                         format: ArchiveExtension = ArchiveExtension.zip):
    with tempfile.TemporaryDirectory(prefix="mlflow-model-", ignore_cleanup_errors=True, delete=True) as tmp_dir:
        tmp_dir = pathlib.Path(tmp_dir)
        mlflow.set_tracking_uri(aggregator)
        try:
            dest_dir = await asyncer.asyncify(mlflow.artifacts.download_artifacts)(artifact_uri=model_uri,
                                                                                   dst_path=str(tmp_dir / "model"),
                                                                                   tracking_uri=aggregator)
        except mlflow.MlflowException as e:
            log.error(e.message)
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND,
                                        detail=f"Model with uri: {model_uri} not found"
                                               f" on tracking sever: {aggregator}")
        comp_file = await asyncer.asyncify(shutil.make_archive)(base_name=str(tmp_dir / "model"),
                                                                format=format.name,
                                                                root_dir=dest_dir)
        comp_file = pathlib.Path(comp_file)
        # return FileResponse(zip_file, media_type="application/octet-stream", filename=zip_file.name)
        ext_type = format.value if format.value in ("zip", "gzip") else f"x-{format.value}"
        return Response(comp_file.read_bytes(),
                        media_type=f"application/{ext_type}",
                        headers={'Content-Disposition': f'attachment; filename="{comp_file.name}"'})


@router.get("/get_model_organizational")
async def get_model_org() -> dict:
    try:
        global_model = await _load_global_model()
        answer = {
            "model_host": global_model["model_host_organizational"],
            "model_uri": global_model["model_uri"],
            # "model_username": os.environ["BASIC_AUTH_USERNAME"],
            "model_password": os.environ["BASIC_AUTH_PASSWORD"]
        }
    except Exception as e:
        print(e)
        answer = {}

    return answer


async def _store_global_model(model_path):
    while os.path.exists(LOCK_NAME):
        print("waiting for lock")
        await asyncio.sleep(np.random.randint(10) / 100)
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
        await asyncio.sleep(np.random.randint(10) / 10)
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


@router.put("/set_global_model")
async def set_global_model(model_path: dict):
    '''
        Sets the global model (URIs).
        Parameters:
            - model_path: a dictionary, describing host's URI (model_host)
                          and the model's URI (model_uri)
    '''
    await _store_global_model(model_path)


def post_train_request(parameters: dict) -> dict:
    share = requests.post(f"{parameters['dp_uri']}/train_model", json=parameters)
    share.raise_for_status()
    return share.json()


@router.post("/start_training")
async def do_training(aggregation_tree: Annotated[
    dict,
    Body(
        examples=[
            {
                "processors": [
                    "http://data-processor-0:8000",
                    "http://data-processor-1:8000"
                ],
                "aggregators": [
                    "http://aggregator:8000"
                ],
                "train_data_uri": [
                    "/data/train_data.npz",
                    "/data/train_data.npz"
                ],
                "aggregation_algorithm": "fedavg"
            }
        ],
    ),
]) -> dict:
    print(aggregation_tree)

    # Train client models:
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

    # Aggregating results:
    if aggregation_tree["aggregation_algorithm"] == "fedavg":
        # For FedAvg:
        aggregation_config = {
            "local_model_hosts": [],
            "local_model_uris": [],
            "local_data_size": [],
            "aggregation_algorithm": "fedavg"
        }
    elif aggregation_tree["aggregation_algorithm"] == "deltarep":
        # For DeltaRep:
        aggregation_config = {
            "local_model_hosts": [],
            "local_model_uris": [],
            "local_data_size": [],
            "aggregation_algorithm": "deltarep",
            "global_model_host": global_model_host,
            "global_model_uri": global_model_uri,
        }

    for sh in shares:
        aggregation_config["local_model_hosts"].append(sh["model_server_host"])
        aggregation_config["local_model_uris"].append(sh["model_share_uri"])
        aggregation_config["local_data_size"].append(sh["n_samples"])

    aggregates = requests.post(f"{aggregation_tree['aggregators'][0]}/aggregate_models", json=aggregation_config)
    aggregates.raise_for_status()
    aggregates = aggregates.json()

    print(aggregates)
    model_dict = {
        "model_host_external": aggregates["aggregated_model_host_external"],
        "model_host_organizational": aggregates["aggregated_model_host_organizational"],
        "model_uri": aggregates["aggregated_model_uri"],
        # "model_username": aggregates["aggregated_model_username"],
        # "model_password": aggregates["aggregated_model_password"]
    }
    await _store_global_model(model_dict)

    answer = {
        "aggregated_model_host": model_dict["model_host_external"],
        "aggregated_model_uri": model_dict["model_uri"],
        # "aggregated_model_username": os.environ["BASIC_AUTH_USERNAME"],
        # "aggregated_model_password": os.environ["BASIC_AUTH_PASSWORD"]
    }
    return answer


########################################################################################################################

app.include_router(router=router)
