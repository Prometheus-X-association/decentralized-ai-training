import asyncio
import logging
import os
from typing import Annotated, Any, Dict
from pydantic import BaseModel
import json

import requests

import fastapi
from fastapi import FastAPI, Body, Response, status

class DeploymentEntry(BaseModel):
    orchestrator_uri: str
    orchestrator_credentials: dict
    mlflow_uri: str
    mlflow_credentials: dict

#TOKEN = os.getenv("GHCR_TOKEN", "blabla")
LOCK_NAME = os.getenv("LOCK_NAME", ".bb01_lock")
REGISTRY_NAME = os.getenv("REGISTRY_NAME", "bb01_registry.json")
CREDENTIAL_NAME = os.getenv("CREDENTIAL_NAME", "credentials.json")

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
    #read credential file:
    with open(CREDENTIAL_NAME) as cred_file:
        cred = json.load(cred_file)

    if validate_ptx_contract_id(ptx_contract_id):
        answer = {
            "ghcr_token": cred["token"]
        }
    else:
        answer = {}
        response.status_code = status.HTTP_400_BAD_REQUEST
    return answer

@app.post("/register_deployment", status_code=status.HTTP_201_CREATED)
async def register_deployment(ptx_contract_id: str,
                              deployment_dict: DeploymentEntry,
                              response: Response) -> dict:
    if validate_ptx_contract_id(ptx_contract_id):
        while os.path.exists(LOCK_NAME):
            await asyncio.sleep(0.1)
        try:
            with open(LOCK_NAME, "w") as lock_file:
                lock_file.write("locked")
                
            deployment_dict = deployment_dict.model_dump()
            log.info(deployment_dict)
            log.info(f"Registering deployment for contract {ptx_contract_id} with orchestrator at {deployment_dict['orchestrator_uri']} and MLflow at {deployment_dict['mlflow_uri']}")
            with open(REGISTRY_NAME, "r") as registry_file:
                registry = json.load(registry_file)
            registry[ptx_contract_id] = deployment_dict
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

@app.post("/remove_deployment", status_code=status.HTTP_200_OK)
async def remove_deployment(ptx_contract_id: str,
                            response: Response) -> dict:
    if validate_ptx_contract_id(ptx_contract_id):
        try:
            while os.path.exists(LOCK_NAME):
                await asyncio.sleep(0.1)

            with open(LOCK_NAME, "w") as lock_file:
                lock_file.write("locked")
            
            with open(REGISTRY_NAME, "r") as registry_file:
                registry = json.load(registry_file)
            del registry[ptx_contract_id]
            with open(REGISTRY_NAME, "w") as registry_file:
                json.dump(registry, registry_file)
            
            os.remove(LOCK_NAME)
        except Exception as e:
            log.error(f"Error deleting contract {ptx_contract_id}: {e}")
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            return {"message": f"Failed to remove deployment for contract {ptx_contract_id}"}
        finally:
            if os.path.exists(LOCK_NAME):
                os.remove(LOCK_NAME)
    else:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"message": f"Invalid contract id: {ptx_contract_id}"}
    return {"message": f"Deployment deleted for contract id: {ptx_contract_id}"}

        

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
                        "mlflow_uri": mlflow_info["mlflow_uri"],
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

@app.get("/get_orchestrator_access", status_code=status.HTTP_200_OK)
async def get_orchestrator_access(ptx_contract_id: str, response: Response) -> dict:
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
                        "orchestrator_uri": mlflow_info["orchestrator_uri"],
                        "orchestrator_credentials": mlflow_info["orchestrator_credentials"]
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

'''@app.post("/start_training", status_code=status.HTTP_200_OK)
async def start_training(ptx_contract_id: str,
                   training_architecture: Annotated[
                       Dict[str, Any],
                       Body(
                           examples = [
                               {
                                   "data_processors": [
                                        {
                                            "uri": "http://data-processor-0:8000",
                                            "target_mlflow": "http://aggregator:8000"
                                        },
                                        {
                                            "uri": "http://data-processor-1:8000",
                                            "target_mlflow": "http://aggregator:8000"
                                        }
                                    ],
                                   "aggregators":
                                    [
                                        {
                                            "uri": "http://aggregator:8000",
                                            "target_mlflow": ""
                                        }
                                    ]
                               }
                           ]
                       )
                    ],
                   response: Response) -> dict:
    if validate_ptx_contract_id(ptx_contract_id):
        try:
            while os.path.exists(LOCK_NAME):
                await asyncio.sleep(0.1)

            with open(LOCK_NAME, "w") as lock_file:
                lock_file.write("locked")
            
                with open(REGISTRY_NAME, "r") as registry_file:
                    registry = json.load(registry_file)
                
                    orchestrator_uri = registry[ptx_contract_id]["orchestrator_uri"]
                    orchestrator_credentials = registry[ptx_contract_id]["orchestrator_credentials"]
            os.remove(LOCK_NAME)

            health_check = requests.get(f"{orchestrator_uri}/health", timeout=10.0)
            if health_check.status_code != 200:
                response.status_code = status.HTTP_503_SERVICE_UNREACHABLE
                raise Exception("Orchestrator unhealthy!")

            print(f"Starting training for contract {ptx_contract_id} with orchestrator at {orchestrator_uri}")
            result = requests.post(
                f"{orchestrator_uri}/start_training",
                json = training_architecture,
                username=orchestrator_credentials["username"], password=orchestrator_credentials["password"]
            )
            
        except Exception as e:
            log.error(f"Error retrieving orchestrator access for contract {ptx_contract_id}: {e}")
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            return {"message": f"Failed to retrieve MLflow access for contract {ptx_contract_id}."}
    answer = {
            "message": f"Training started for contract {ptx_contract_id}"
    }
    return answer'''