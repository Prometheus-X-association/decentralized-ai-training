import asyncio
import logging
import os
from typing import Annotated, Any, Dict
import json

import requests

import fastapi
from fastapi import FastAPI, Body, Response, status

TOKEN = os.getenv("GHCR_TOKEN", "blabla")
LOCK_NAME = os.getenv("LOCK_NAME", ".bb01_lock")
REGISTRY_NAME = os.getenv("REGISTRY_NAME", "bb01_registry.json")

log = logging.getLogger(__name__)
app = FastAPI(title="Decentralized AI-training BB - API", version="0.1.0", root_path="/")

def validate_ptx_contract_id(ptx_contract_id: str) -> bool:
    return len(ptx_contract_id) > 0

########################################### API ENDPOINTS #################################################################
@app.api_route("/health", methods=["GET", "HEAD"], status_code=fastapi.status.HTTP_200_OK)
async def health_check():
    pass


@app.get("/get_algorithm_credentials", status_code=status.HTTP_200_OK)
def get_algorithm_credentials(ptx_contract_id: str, response: Response) -> dict:
    
    if validate_ptx_contract_id(ptx_contract_id):
        answer = {
            "ghcr_token": TOKEN
        }
    else:
        answer = {}
        response.status_code = status.HTTP_400_BAD_REQUEST
    return answer

@app.post("/register_deployment", status_code=status.HTTP_201_CREATED)
async def register_deployment(ptx_contract_id: str,
                        orchestrator_endpoint: str,
                        orchestrator_credentials: Annotated[dict, Body()],
                        mlflow_endpoint: str,
                        mlflow_credentials: Annotated[dict, Body()],
                        response: Response) -> dict:
    if validate_ptx_contract_id(ptx_contract_id):
        while os.path.exists(LOCK_NAME):
            await asyncio.sleep(0.1)
        try:
            with open(LOCK_NAME, "w") as lock_file:
                lock_file.write("locked")
                
                log.info(f"Registering deployment for contract {ptx_contract_id} with orchestrator at {orchestrator_endpoint} and MLflow at {mlflow_endpoint}")
                with open(REGISTRY_NAME, "r") as registry_file:
                    registry = json.load(registry_file)
                registry[ptx_contract_id] = {
                    "orchestrator_endpoint": orchestrator_endpoint,
                    "orchestrator_credentials": orchestrator_credentials,
                    "mlflow_endpoint": mlflow_endpoint,
                    "mlflow_credentials": mlflow_credentials
                }
                with open(REGISTRY_NAME, "w") as registry_file:
                    json.dump(registry, registry_file)
                os.remove(LOCK_NAME)
        except Exception as e:
            log.error(f"Error registering deployment for contract {ptx_contract_id}: {e}")
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            return {"message": f"Failed to register deployment for contract {ptx_contract_id}."}
        finally:
            if os.path.exists(LOCK_NAME):
                os.remove(LOCK_NAME)
        answer = {
            "message": f"Deployment for contract {ptx_contract_id} registered successfully."
        }
    else:
        answer = {}
        response.status_code = status.HTTP_400_BAD_REQUEST
    return answer

@app.get("/get_federated_mlflow_access", status_code=status.HTTP_200_OK)
async def get_federated_mlflow_access(ptx_contract_id: str, response: Response) -> dict:
    if validate_ptx_contract_id(ptx_contract_id):
        try:
            while os.path.exists(LOCK_NAME):
                await asyncio.sleep(0.1)

            with open(LOCK_NAME, "w") as lock_file:
                lock_file.write("locked")
            
                with open(REGISTRY_NAME, "r") as registry_file:
                    registry = json.load(registry_file)
                
                    if ptx_contract_id in registry:
                        mlflow_info = registry[ptx_contract_id]
                        answer = {
                            "mlflow_endpoint": mlflow_info["mlflow_endpoint"],
                            "mlflow_credentials": mlflow_info["mlflow_credentials"]
                        }
                    else:
                        answer = {}
                        response.status_code = status.HTTP_404_NOT_FOUND

            os.remove(LOCK_NAME)
            
        except Exception as e:
            log.error(f"Error retrieving MLflow access for contract {ptx_contract_id}: {e}")
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            return {"message": f"Failed to retrieve MLflow access for contract {ptx_contract_id}."}
        finally:
            if os.path.exists(LOCK_NAME):
                os.remove(LOCK_NAME)
    else:
        answer = {}
        response.status_code = status.HTTP_400_BAD_REQUEST
    return answer

@app.post("/start_training", status_code=status.HTTP_200_OK)
async def start_training(ptx_contract_id: str,
                   training_architecture: Dict[str, Any],
                   response: Response) -> dict:
    if validate_ptx_contract_id(ptx_contract_id):
        try:
            while os.path.exists(LOCK_NAME):
                await asyncio.sleep(0.1)

            with open(LOCK_NAME, "w") as lock_file:
                lock_file.write("locked")
            
                with open(REGISTRY_NAME, "r") as registry_file:
                    registry = json.load(registry_file)
                
                    orchestrator_uri = registry[ptx_contract_id]["orchestrator_endpoint"]
                    orchestrator_credentials = registry[ptx_contract_id]["orchestrator_credentials"]
            os.remove(LOCK_NAME)

            print(f"Starting training for contract {ptx_contract_id} with orchestrator at {orchestrator_uri}")
            result = requests.post(
                f"{orchestrator_uri}/start_training",
                json = training_architecture,
                username=orchestrator_credentials["username"], password=orchestrator_credentials["password"]
            )
            
        except Exception as e:
            log.error(f"Error retrieving MLflow access for contract {ptx_contract_id}: {e}")
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            return {"message": f"Failed to retrieve MLflow access for contract {ptx_contract_id}."}
    answer = {
            "message": f"Training started for contract {ptx_contract_id}"
    }
    return answer