import numpy as np
import requests
import mlflow
import pytest
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, mean_absolute_error
import os

# Helper functions for testing mlflow authentication and model training
# One for training a simple model and pushing it to mlflow, and another for pulling the model.

def push_model_to_mlflow(experiment_name):
    mlflow.set_experiment(experiment_name)
    mlflow.sklearn.autolog()

    # Minimal dummy data for training a model
    x = np.array([1, 2, 3, 4, 5])
    y = np.array([2, 4, 5, 4, 5])

    model = LinearRegression()

    with mlflow.start_run() as run:
        model.fit(x.reshape(-1, 1), y)
        predictions = model.predict(x.reshape(-1, 1))
        mse = mean_squared_error(y, predictions)
        mae = mean_absolute_error(y, predictions)

        mlflow.log_metric("mse", mean_squared_error(y, predictions))
        mlflow.log_metric("mae", mean_absolute_error(y, predictions))
        return run.info.run_id


def pull_model_from_mlflow(experiment_name):
    # Search the experiment and retrieve the runs
    experiment = mlflow.get_experiment_by_name(experiment_name)
    runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id])
    # Get the latest run
    latest_run = runs.iloc[0]
    # Load the model from the latest run
    model = mlflow.sklearn.load_model(f"runs:/{latest_run.run_id}/model")
    return model

# ---------------------------------------------------------------------------
# 0. Test: Service is up
# ---------------------------------------------------------------------------
def test_aggregator_health(aggregator_container, health_port):
    response = requests.get(f"http://localhost:{health_port}/health")
    assert response.status_code == 200

# ---------------------------------------------------------------------------
# 1. Test: Any unauthenticated request to mlflow should fail
# ---------------------------------------------------------------------------
def test_unauthenticated_request_is_rejected(aggregator_container, tracking_uri):
    response = requests.get(f"{tracking_uri}/#/experiments")
    assert response.status_code == 401

# ---------------------------------------------------------------------------
# 2. Test: Admin authentication should succeed
# ---------------------------------------------------------------------------
def test_admin_can_send_authenticated_requests(aggregator_container, admin_config, tracking_uri):
    response = requests.get(
        f"{tracking_uri}/#/experiments", 
        auth=('admin', admin_config["admin_password"])
    )
    assert response.status_code == 200
    
def test_admin_can_authenticate_with_mlflow(aggregator_container, experiment_name, as_user):
    as_user("admin")
    mlflow.set_experiment(experiment_name)

# ---------------------------------------------------------------------------
# 3. Test: Pushing model permissions
# ---------------------------------------------------------------------------
# As an aggregator, we should be able to push a model to mlflow
def test_aggregator_can_push_model(aggregator_container, as_user, experiment_name):
    as_user("aggregator")
    run_id = push_model_to_mlflow(experiment_name)
    assert run_id is not None

# As a model user, we should not be able to push a model to mlflow and should get a 403 unauthorized error
def test_model_user_cannot_push_model(aggregator_container, as_user, experiment_name):
    as_user("model_user")
    with pytest.raises(mlflow.exceptions.MlflowException) as exc_info:
        push_model_to_mlflow(experiment_name)
    assert "403" in str(exc_info.value) or "Permission denied" in str(exc_info.value)

# As unauthenticated user, we should get unauthenticated 401 error when trying to push a model to mlflow
def test_unauthenticated_user_cannot_push_model(aggregator_container, experiment_name):
    with pytest.raises(mlflow.exceptions.MlflowException) as exc_info:
        push_model_to_mlflow(experiment_name)
    assert "401" in str(exc_info.value)

# ---------------------------------------------------------------------------
# 4. Test: Pulling model permissions
# ---------------------------------------------------------------------------
# Both the aggregator and model user should be able to pull a model from mlflow
@pytest.mark.parametrize("role", ["aggregator", "model_user"])
def test_aggregator_and_model_user_can_pull_model(aggregator_container, as_user, role, experiment_name):
    as_user(role)
    model = pull_model_from_mlflow(experiment_name)
    assert model is not None

# As unauthenticated user, we should get unauthenticated 401 error when trying to pull a model from mlflow
def test_unauthenticated_user_cannot_pull_model(aggregator_container, experiment_name):
    with pytest.raises(mlflow.exceptions.MlflowException) as exc_info:
        pull_model_from_mlflow(experiment_name)
    assert "401" in str(exc_info.value)