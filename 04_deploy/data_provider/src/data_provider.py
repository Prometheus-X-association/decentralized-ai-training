import os
import pathlib

import fastapi
from fastapi import FastAPI
from fastapi.responses import FileResponse

app = FastAPI()


@app.api_route("/health", methods=["GET", "HEAD"], status_code=fastapi.status.HTTP_200_OK)
async def health_check():
    pass


@app.get("/get_data")
async def get_data(dp_id: str):
    '''
        Sends training data
        Parameters:
            - train_id: name of the data processor, i.e., 'dp1' or 'dp2'
        Returns:
            - corresponding training data file                
    '''
    file_path = pathlib.Path(os.environ["DATA_PATH"], dp_id, "train_data.npz")
    return FileResponse(file_path, media_type="application/octet-stream", filename=file_path.name)
