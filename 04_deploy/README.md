# Deployment

## Training data

Copy the training data into `02_data`,
e.g., `02_data/dp1/train_data.npz` and `02_data/dp2/train_data.npz`.

## Image building

For the first step, run the building script directly:

```bash
$ ./build_images.sh
```

After that, docker images can be rebuilt by `docker compose`:

```bash
$ docker compose build
```

## Local deployment

```bash
$ docker compsoe up
```

To tear down the setup, use

```bash
$ docker compose down
```

Also, to delete cache, use

```bash
$ docker compose down -v
```

## Artifact download

```bash
# on alpine
apk add python3 py3-pip

pip3 install mlflow-skinny
```

Example from Python:
```python
import mlflow
import os

os.environ['MLFLOW_TRACKING_URI']="https://vm.fured.cloud.bme.hu:19953/worker/aggregator"
os.environ['MLFLOW_TRACKING_USERNAME']="admin"
os.environ['MLFLOW_TRACKING_PASSWORD']="admin"
os.environ["MLFLOW_TRACKING_INSECURE_TLS"]="True"

#mlflow.set_tracking_uri("https://vm.fured.cloud.bme.hu:19953/worker/aggregator")
mlflow.artifacts.download_artifacts(artifact_uri="mlflow-artifacts:/0/models/m-de4345cb04af4050a131805555783f73/artifacts",
                                    dst_path="./model")

mlflow.artifacts.download_artifacts(artifact_uri="models:/m-de4345cb04af4050a131805555783f73",
                                    tracking_uri="https://vm.fured.cloud.bme.hu:19953/worker/aggregator",
                                    dst_path="./model2")
```

Example from bash:
```bash
$ mkdir test && cd test
~/test$ python3 -m venv .venv
~/test$ source .venv/bin/activate
~/test$ pip3 install mlflow
~/test$ export MLFLOW_TRACKING_URI=https://vm.fured.cloud.bme.hu:19953/worker/aggregator
~/test$ export MLFLOW_TRACKING_USERNAME=admin
~/test$ export MLFLOW_TRACKING_PASSWORD=admin
~/test$ export MLFLOW_TRACKING_INSECURE_TLS=True
~/test$ mlflow artifacts download -u mlflow-artifacts:/0/models/m-40d3371e830b48d886913b9b7db5693f/artifacts -d ./model
```