#!/bin/bash

./build_images.sh build_base

docker push ghcr.io/alelevente/edge_base:latest
docker push ghcr.io/alelevente/data_processor:latest
docker push ghcr.io/alelevente/aggregator:latest
docker push ghcr.io/alelevente/orchestrator:latest

