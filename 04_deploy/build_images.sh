#!/usr/bin/env bash
set -eou pipefail

cp ../03_dev/model.py aggregator/src/model.py
cp ../03_dev/model.py data_processor/src/model.py
cp ../03_dev/share_sim/share_tools.py data_processor/src/share_tools.py

rm -rfv data_provider/data
mkdir -p data_provider/data/dp1
mkdir -p data_provider/data/dp2

if [ -d ../02_data/dp1 ] && [ -d ../02_data/dp2 ] && \
        [ "$(ls -A ../02_data/dp1/ | wc -w)" -gt 0 ] && [ "$(ls -A ../02_data/dp2/ | wc -w)" -gt 0 ]; then
    cp ../02_data/dp1/* data_provider/data/dp1
    cp ../02_data/dp2/* data_provider/data/dp2
else
    echo -e "\nMissing training data from ../02_data/ !!!"
    exit 1
fi

for img in base_* data_provider data_processor orchestrator; do
    pushd "${img}"
        docker build . -t "ghcr.io/alelevente/${img}:latest" --no-cache
    popd
done

docker build -f aggregator/Dockerfile.agg -t "ghcr.io/alelevente/aggregator:latest" --no-cache aggregator
docker build -f aggregator/Dockerfile.tlagg -t "ghcr.io/alelevente/top-level-aggregator:latest" --no-cache aggregator

