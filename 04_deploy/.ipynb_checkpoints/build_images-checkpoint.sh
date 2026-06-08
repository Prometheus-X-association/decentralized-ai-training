#!/bin/bash

cp ../03_dev/model.py aggregator/src/model.py
cp ../03_dev/model.py data_processor/src/model.py

rm -r data_provider/data
mkdir data_provider/data
mkdir data_provider/data/dp1
mkdir data_provider/data/dp2
cp ../02_data/dp1/* data_provider/data/dp1
cp ../02_data/dp2/* data_provider/data/dp2


if [ $# -eq 1 ]
	then
		cd base
		docker build . -t ghcr.io/alelevente/edge_base:latest --no-cache
		cd ..
fi

cd aggregator
docker build . -t ghcr.io/alelevente/aggregator:latest --no-cache
cd ..

cd data_processor
docker build . -t ghcr.io/alelevente/data_processor:latest --no-cache
cd ..

cd orchestrator
docker build . -t ghcr.io/alelevente/orchestrator:latest --no-cache
cd ..

