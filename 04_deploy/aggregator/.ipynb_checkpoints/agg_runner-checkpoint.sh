#!/bin/bash

STATIC_PREFIX="${STATIC_PREFIX:-/}"

mlflow server --host=0.0.0.0 --port=5000 --disable-security-middleware & #--static-prefix="${STATIC_PREFIX}" &

fastapi run aggregator.py --host=0.0.0.0 --port=8000 --workers=2
