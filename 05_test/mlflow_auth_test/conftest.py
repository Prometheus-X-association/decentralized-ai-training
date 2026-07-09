"""Shared confitguration for all tests in this directory and below, 
so used for mlflow server authenticaton testing."""
import json
import os
import pytest
import subprocess
import time
import mlflow
import requests

BASE_IMAGE_DIR = "04_deploy/base_slim"
BASE_IMAGE = "ghcr.io/alelevente/base-slim:latest"
AGGREGATOR_DOCKERFILE_DIR = os.environ.get("AGGREGATOR_DOCKERFILE_DIR", "04_deploy/aggregator")
AGGREGATOR_IMAGE = os.environ.get("AGGREGATOR_IMAGE", "ghcr.io/alelevente/aggregator:latest")
CONTAINER_NAME = "mlflow-auth-test"
MLFLOW_PORT = 5100
AGGREGATOR_HEALTH_PORT = 9100

MLFLOW_TRACKING_URI = f"http://localhost:{MLFLOW_PORT}"
HEALTH_URI = f"http://localhost:{AGGREGATOR_HEALTH_PORT}/health"
MLFLOW_EXPERIMENT_NAME = "edge-fl-experiment"


# Polling the health endpoint instead of guessing a fixed sleep duration, to make sure the mlflow server is started up
def _wait_for_health(url: str, timeout: int = 30, interval: float = 0.5) -> None:
    """Poll a health endpoint instead of guessing a fixed sleep duration."""
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                return
        except requests.exceptions.RequestException as exc:
            last_error = exc
        time.sleep(interval)
    raise RuntimeError(
        f"Service at {url} did not become healthy within {timeout}s: {last_error}"
    )

def _wait_for_auth_ready(tracking_uri: str, username: str, password: str,
                          timeout: int = 30, interval: float = 0.5) -> None:
    """Poll until a non-admin user can actually authenticate against MLflow.
    /health passing only means the process is up; it says nothing about
    whether the auth DB has finished provisioning custom users yet."""
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            resp = requests.get(f"{tracking_uri}/#/experiments", auth=(username, password), timeout=2)
            if resp.status_code == 200:
                return
            last_error = f"status {resp.status_code}"
        except requests.exceptions.RequestException as exc:
            last_error = exc
        time.sleep(interval)
    raise RuntimeError(f"User '{username}' not authenticated within {timeout}s: {last_error}")



# Starting the main container for the tests, which is the aggregator container that runs mlflow server with authentication enabled
@pytest.fixture(scope="session")
def aggregator_container(admin_config): 
    """Build the aggregator image, run it, wait for it to be healthy,
    yield control to the tests, then always clean up."""
    subprocess.run(["docker", "build", BASE_IMAGE_DIR, "-t", BASE_IMAGE], check=True)

    subprocess.run(
        ["docker", "build", AGGREGATOR_DOCKERFILE_DIR, "-t", AGGREGATOR_IMAGE, "--no-cache"],
        check=True
    )
    subprocess.run(
        [ "docker", "run", "--name", CONTAINER_NAME, "-d", "--rm",
            "-p", f"{MLFLOW_PORT}:5000",
            "-p", f"{AGGREGATOR_HEALTH_PORT}:8000",
            AGGREGATOR_IMAGE],
        check=True
    )
    try:
        _wait_for_health(HEALTH_URI, timeout=60)
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        _wait_for_auth_ready(MLFLOW_TRACKING_URI, "aggregator", admin_config["aggregator_password"])
        _wait_for_auth_ready(MLFLOW_TRACKING_URI, "model_user", admin_config["model_user_password"])

        yield
    finally:
        subprocess.run(["docker", "stop", CONTAINER_NAME], check=True)


@pytest.fixture(scope="session")
def admin_config():
    """Load role passwords.
 
    In CI these come from GitHub Actions secrets exposed as env vars
    (ADMIN_PASSWORD / AGGREGATOR_PASSWORD / MODEL_USER_PASSWORD) so no
    credentials file needs to exist in the repo. Locally, fall back to
    the same cfg/mlflow_admin.json file the notebook used, so nothing
    changes for people still experimenting in notebooks.
    """
    env_keys = {
        "admin_password": "ADMIN_PASSWORD",
        "aggregator_password": "AGGREGATOR_PASSWORD",
        "model_user_password": "MODEL_USER_PASSWORD",
    }
    if all(os.environ.get(v) for v in env_keys.values()):
        return {k: os.environ[v] for k, v in env_keys.items()}
 
    config_path = os.path.join(
        AGGREGATOR_DOCKERFILE_DIR, "cfg", "mlflow_admin.json"
    )
    with open(config_path) as f:
        return json.load(f)
 
 
@pytest.fixture(autouse=True)
def clear_mlflow_credentials():
    """Ensure every test starts unauthenticated and leaves no
    credentials behind for the next test."""
    os.environ.pop("MLFLOW_TRACKING_USERNAME", None)
    os.environ.pop("MLFLOW_TRACKING_PASSWORD", None)
    yield
    os.environ.pop("MLFLOW_TRACKING_USERNAME", None)
    os.environ.pop("MLFLOW_TRACKING_PASSWORD", None)
 
 
@pytest.fixture
def as_user(admin_config):
    """Factory fixture: as_user('aggregator') sets tracking credentials
    for that role for the duration of a test."""
    def _set(role: str):
        os.environ["MLFLOW_TRACKING_USERNAME"] = role
        os.environ["MLFLOW_TRACKING_PASSWORD"] = admin_config[f"{role}_password"]
    return _set

@pytest.fixture
def experiment_name():
    """Fixture to get the experiment name."""
    return MLFLOW_EXPERIMENT_NAME

@pytest.fixture
def tracking_uri():
    """Fixture to get the tracking URI."""
    return MLFLOW_TRACKING_URI

@pytest.fixture
def health_port():
    """Fixture to get the health port."""
    return AGGREGATOR_HEALTH_PORT
 