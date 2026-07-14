import os
from typing import Annotated, Any, Dict
from pydantic import BaseModel
import json

import requests

import fastapi
from fastapi import FastAPI, Body, Response, status

EXAMPLE_DEPLOYMENT_JSON = {
    "orchestrator_uri": "https://orchestrator.mydeployment.company.com",
    "orchestrator_credentials": {
        "username": "my_orchestrator_user",
        "password": "my_orchestrator_password"
    },
    "mlflow_uri": "https://mlflow.topaggregator.mydeployment.company.com",
    "mlflow_credentials": {
        "username": "my_mlflow_user",
        "password": "my_mlflow_password"
    }
}

app = FastAPI(title="PDC tester", version="0.1.0", root_path="/")

def write_pdc_request(contract_id: str,
                      consumer_offer_id: str,
                      provider_offer_id: str,
                      provider_resource_id: str,
                      consumer_resource_id: str,
                      provider_parameters: list[dict] = {},
                      consumer_parameters: list[dict] = {}) -> dict:
    pdc_req = dict()
    pdc_req["contract"] = f"https://contract.visionstrust.com/contracts/{contract_id}"
    pdc_req["purposeId"] = f"https://api.visionstrust.com/v1/catalog/serviceofferings/{consumer_offer_id}"
    pdc_req["resourceId"] = f"https://api.visionstrust.com/v1/catalog/serviceofferings/{provider_offer_id}"
    pdc_req["resources"] = [{
        "resource": f"https://api.visionstrust.com/v1/catalog/dataresources/{provider_resource_id}",
        "params": {
            "query": provider_parameters
        }
    }]
    pdc_req["purposes"] = [{
        "resource": f"https://api.visionstrust.com/v1/catalog/softwareresources/{consumer_resource_id}"
    }]
    pdc_req["consumerParams"] = {
        "query": consumer_parameters
    }
    return json.dumps(pdc_req)
    
@app.post("/pdc_login")
async def login(pdc_connector_uri: str,
                pdc_secret_key: str,
                pdc_service_key: str) -> dict:
    login_request = {
        "secretKey": pdc_secret_key,
        "serviceKey": pdc_service_key
    }

    login_request_json = json.dumps(login_request)

    response = requests.post(f"{pdc_connector_uri}/login",
                             headers={"Content-Type": "application/json"},
                             data=login_request_json)
    return response.json()

@app.post("/test_api_credentials")
async def get_credentials(pdc_connector_uri: str,
                          contract_id: str,
                          consumer_offer_id: str,
                          provider_offer_id: str,
                          credential_download_resource_id: str,
                          credential_process_resource_id: str,
                          token: str
                          ) -> dict:
    
    pdc_query = write_pdc_request(contract_id, consumer_offer_id, provider_offer_id,
                                  credential_download_resource_id, credential_process_resource_id,
                                  provider_parameters=[{"ptx_contract_id": contract_id}])
    response = requests.post(f"{pdc_connector_uri}/consumer/exchange",
                  data=pdc_query,
                  headers={"Content-Type": "application/json",
                           "Authorization": f"Bearer {token}"})
    return response.json()

@app.post("/test_api_register_deployment")
async def register_deployment(pdc_connector_uri: str,
                              contract_id: str,
                              consumer_offer_id: str,
                              provider_offer_id: str,
                              register_deployment_resource_id: str,
                              register_process_resource_id: str,
                              token: str,
                              deployment_json: dict = Body(
                                  openapi_example=EXAMPLE_DEPLOYMENT_JSON
                              )) -> dict:
    pdc_query = write_pdc_request(contract_id, consumer_offer_id, provider_offer_id,
                                  register_deployment_resource_id, register_process_resource_id,
                                  provider_parameters=[{"deployment_dict": deployment_json}])
    response = requests.post(f"{pdc_connector_uri}/consumer/exchange",
                  data=pdc_query,
                  headers={"Content-Type": "application/json",
                           "Authorization": f"Bearer {token}"})
    return response.json()


@app.post("/test_api_orchestrator_access")
async def orchestrator_access(pdc_connector_uri: str,
                              contract_id: str,
                              consumer_offer_id: str,
                              provider_offer_id: str,
                              orchestrator_access_resource_id: str,
                              orchestrator_process_resource_id: str,
                              token: str) -> dict:
    pdc_query = write_pdc_request(contract_id, consumer_offer_id, provider_offer_id,
                                  orchestrator_access_resource_id, orchestrator_process_resource_id,
                                  provider_parameters=[{"ptx_contract_id": contract_id}])
    response = requests.post(f"{pdc_connector_uri}/consumer/exchange",
                  data=pdc_query,
                  headers={"Content-Type": "application/json",
                           "Authorization": f"Bearer {token}"})
    return response.json()