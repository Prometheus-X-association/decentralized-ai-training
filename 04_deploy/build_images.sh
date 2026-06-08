#!/usr/bin/env bash
set -eou pipefail

cp ../03_dev/model.py aggregator/src/model.py
cp ../03_dev/model.py data_processor/src/model.py

rm -r data_provider/data
mkdir -p data_provider/data/dp1
mkdir -p data_provider/data/dp2
cp ../02_data/dp1/* data_provider/data/dp1
cp ../02_data/dp2/* data_provider/data/dp2


for img in base_* data_provider data_processor aggregator orchestrator; do
    pushd "${img}"
        docker build . -t "ghcr.io/alelevente/${img}:latest" --no-cache
    popd
done

