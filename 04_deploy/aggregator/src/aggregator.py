import os

import fastapi
import numpy as np
from fastapi import FastAPI, Response, APIRouter


import agg_helper

LOCK_NAME = ".edge_fl_lock"
TEST_DATA_PATH = "/data/course_test.npz"

MODELS_PATH = os.getenv("MODELS_PATH", "models")

app = FastAPI(title="Aggregator")

@app.api_route("/health", methods=["GET", "HEAD"], status_code=fastapi.status.HTTP_200_OK)
async def health_check():
    pass


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
    combined_model = await agg_helper.aggregate_models(aggregation_config, LOCK_NAME, MODELS_PATH, TEST_DATA_PATH)

    if "forward_model_to" in aggregation_config:
        model_id = await agg_helper.forward_model(combined_model, aggregation_config["forward_model_to"][0], LOCK_NAME)

    return {"model_id": model_id}


########################################################################################################################

app.include_router(router=router)
