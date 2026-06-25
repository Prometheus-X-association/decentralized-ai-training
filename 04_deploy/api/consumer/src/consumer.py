import asyncio
import logging
import os
from typing import Annotated, Any, Dict
from pydantic import BaseModel
import json

import requests

import fastapi
from fastapi import FastAPI, Body, Response, status

app = FastAPI(title="PDC Consumer", version="0.1.0", root_path="/")

@app.post("/process_response", status_code=status.HTTP_200_OK)
async def process_response(content: dict) -> dict:
    print(content)
    answer = {
        "response": "message received"
    }
    return answer