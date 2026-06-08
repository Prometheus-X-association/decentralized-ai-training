#!/bin/bash

ROOT_PATH="${ROOT_PATH:-/}"

fastapi run orchestrator.py --host=0.0.0.0 --port=8000 --workers=4 \
                            --proxy-headers --forwarded-allow-ips="*" #--root-path="${ROOT_PATH}"