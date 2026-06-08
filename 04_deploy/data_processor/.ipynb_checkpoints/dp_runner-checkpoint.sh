#!/bin/bash

mlflow server --host 0.0.0.0 --disable-security-middleware --allowed-hosts \"172.28.*,localhost:*\" --port 5000  &

fastapi run --workers 2 data_processor.py --host 0.0.0.0 --port 8000