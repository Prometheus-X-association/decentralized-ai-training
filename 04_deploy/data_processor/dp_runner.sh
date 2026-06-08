#!/usr/bin/env bash

mlflow server --host=0.0.0.0 --disable-security-middleware --allowed-hosts="172.28.*,localhost:*" --port=5000 &
uvicorn data_processor:app --app-dir=src --workers=2 --host=0.0.0.0 --port=8000 &

# Wait for first exiting job and return with its return value
wait -np RETVAL # requires bash
exit ${RETVAL:-1}