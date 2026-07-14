# Decentralized AI training BB

This building block allows its users to create a machine learning model in a *federated learning* manner.

## Design Document
See the design document [here](01_docs/design-document.md).

## Building instructions
One can build the BB's images by running:

```bash
$ cd 04_deployment
$ ./build_images.sh
```

## Running instructions
There are two types of deployment of this BB.

### Docker compose-based test environment

For a simple test deployment in `docker compose`, one can run the following commands:
```bash
$ cd 04_deployment
$ ./deploy.sh --test-deploy
```

### Kubernetes-based production deployment
For a full-fleged deployment, follow the procedure below:

1. Run the following comands (on local computer) to build and push the BB's images to a repository:
```bash
    $ cd 04_deployment
    04_deployment$ ./deploy.sh --cluster-deploy
```

2. Publish files for BB01-API from local computer to e.g. `cloud.bme.hu` (if it is your responsibility to run it). Note that it will publish itself to the PTX-Catalogue!
```bash
    04_deployment$ cd api
    04_deployment/api$ ./deploy_to_fured.sh <port> <password>
```

2. Set BB01's API up to provide PDC access with the following codes:
```bash
TBA
```

3. Follow cluster deployment instructions in [BB02 Edge computing](https://github.com/Prometheus-X-association/edge-computing/tree/main/kubernetes/deployment/training).

## Example usage

### Core functionality
The BB itself provides two endpoints:
- an interface to its Orchestrator component
- an [`MLFLow server`](https://mlflow.org/docs/latest/ml/) to provide access for the trained AI model

To use the BB, send the following requests to the designated endpoints:
| Endpoint                    | Example input | Expected output   |
| --------------------------- | ------------- | ----------------- |
| orchestrator/start_training | {[`aggregation_tree`](01_docs/dynamics.md#BB01-usage)}         | 200 OK, `{"model_uri": "top-level-aggregator/mlflow:324seuioz5u"}` |
| top-level-aggregator/mlflow | `mlflow.tensorflow.load_model(model_uri) `              | a loaded `tensorflow` model instance   |

### BB01 API via PDC
BB01 also provides credentials for project partners through Prometheus-X Data Connectors (PDCs). For more details, please refer to [the documentation](01_docs/dynamics.md).


## Unit testing
### Setup test environment

```bash
$ cd 04_deployment
$ ./deploy.sh --test-deploy
```

### Run tests
### Expected results

## Component-level testing
### Setup test environment
### Run tests
### Expected results
