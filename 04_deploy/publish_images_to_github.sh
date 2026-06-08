#!/bin/bash

if [ $# -eq 1 ]
	then
		./build_images.sh build_base
		docker push ghcr.io/alelevente/edge_base:latest
	else
		./build_images.sh
fi


docker push ghcr.io/alelevente/data_processor:latest
docker push ghcr.io/alelevente/aggregator:latest
docker push ghcr.io/alelevente/orchestrator:latest

