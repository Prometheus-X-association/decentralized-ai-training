import os
from typing import Annotated, Any, Dict
from pydantic import BaseModel
import json

import requests

import fastapi
from fastapi import FastAPI, Body, Response, status

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
    return pdc_req
    

@app.post("/test_api_credentials")
async def get_credentials(pdc_connector_uri: str,
                          contract_id: str,
                          consumer_offer_id: str,
                          provider_offer_id: str,
                          credential_download_resource_id: str,
                          credential_process_resource_id: str
                          ) -> dict:
    
    pdc_query = write_pdc_request(contract_id, consumer_offer_id, provider_offer_id,
                                  credential_download_resource_id, credential_process_resource_id)
    response = requests.post(f"{pdc_connector_uri}/consumer/exchange",
                  data=pdc_query,
                  headers={"Content-Type": "application/json",})# "Authorization"})
    return response.content()