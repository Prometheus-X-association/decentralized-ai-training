#!/bin/bash

fastapi run --workers 2 data_provider.py --host 0.0.0.0 --port 8000
