#!/usr/bin/env bash

if [ -n "${STATIC_PREFIX_MLFLOW}" ]; then
    ARG="--static-prefix=${STATIC_PREFIX_MLFLOW}"
fi

# Initiate processes
# shellcheck disable=SC2086
mlflow server --app-name basic-auth --host=0.0.0.0 --port=5000 --disable-security-middleware ${ARG:-} &
uvicorn aggregator:app --app-dir=src --host=0.0.0.0 --port=8000 --workers=2 --proxy-headers --forwarded-allow-ips='*' &

# Wait for first exiting job and return with its return value
wait -np RETVAL # requires bash
exit ${RETVAL:-1}