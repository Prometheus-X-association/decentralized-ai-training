import json
import os

import numpy as np

from fastapi import FastAPI, Response
from fastapi.responses import FileResponse


app = FastAPI()

    
@app.api_route("/health", methods=["GET", "HEAD"])
async def health_check():
    return Response(status_code=200)
    
        

@app.get("/get_data")
async def get_data(dp_id: str):
    '''
        Sends training data
        Parameters:
            - train_id: name of the data processor, i.e., 'dp1' or 'dp2'
        Returns:
            - corresponding training data file                
    '''

    file_path = f"{os.environ["DATA_PATH"]}/{dp_id}/train_data.npz"
    
    return FileResponse(file_path)
