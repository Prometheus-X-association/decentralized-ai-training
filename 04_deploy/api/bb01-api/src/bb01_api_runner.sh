#!/bin/bash

#auto-login to PDC and get the bearer token for the API:
export PDC_TOKEN=`./login.sh | grep -Po "(?<=Bearer token: ).*"`

#run server:
fastapi run ./bb01_api.py --workers 2 --host 0.0.0.0 --port 8000