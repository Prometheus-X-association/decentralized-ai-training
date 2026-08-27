#!/usr/bin/env bash

uvicorn data_processor:app --app-dir=src --workers=2 --host=0.0.0.0 --port=8000 &

# Wait for first exiting job and return with its return value
wait -np RETVAL # requires bash
exit ${RETVAL:-1}