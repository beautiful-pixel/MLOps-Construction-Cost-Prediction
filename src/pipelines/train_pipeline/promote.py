"""
Model promotion logic.

Compare a candidate run against the current production model
based on reference test metrics.

Promote candidate if it performs better.
"""
import logging
import os
from typing import Optional

import mlflow
from mlflow.tracking import MlflowClient
from mlflow.exceptions import MlflowException, RestException

from utils.mlflow_config import get_model_name


REFERENCE_METRIC = "reference_rmsle"   # metric used for comparison
HIGHER_IS_BETTER = False              # True for r2, False for mse


def _get_metric_from_run(run_id: str, metric_name: str) -> Optional[float]:
    client = MlflowClient()
    run = client.get_run(run_id)
    return run.data.metrics.get(metric_name)

def _get_production_run_id(model_name: str) -> Optional[str]:
    client = MlflowClient()

    try:
        versions = client.get_latest_versions(
            model_name,
            stages=["Production"],
        )
    except MlflowException:
        # Registered model does not exist yet
        return None

    if not versions:
        return None

    return versions[0].run_id

def _is_better(new: float, old: Optional[float], mode: str) -> bool:
    if old is None:
        return True
    if mode == "min":
        return new < old
    if mode == "max":
        return new > old
    raise ValueError("mode must be 'min' or 'max'")


def promote_if_better(run_id: str) -> bool:
    """
    Promote model to Production stage if better than current one.

    Args:
        run_id: Candidate MLflow run ID.

    Returns:
        True if promoted, False otherwise.
    """

    model_name = get_model_name()
    client = MlflowClient()

    # Candidate metric
    candidate_metric = _get_metric_from_run(run_id, REFERENCE_METRIC)

    if candidate_metric is None:
        raise ValueError(
            f"Metric '{REFERENCE_METRIC}' not found in run {run_id}"
        )

    # Get current production model
    production_run_id = _get_production_run_id(model_name)

    # If no model in production -> promote directly
    if production_run_id is None:

        model_uri = f"runs:/{run_id}/model"

        result = mlflow.register_model(model_uri, model_name)

        client.transition_model_version_stage(
            name=model_name,
            version=result.version,
            stage="Production",
        )

        return True

    # Compare metrics
    production_metric = _get_metric_from_run(
        production_run_id,
        REFERENCE_METRIC,
    )

    if production_metric is None:
        raise ValueError(
            f"Metric '{REFERENCE_METRIC}' not found in production run"
        )

    if HIGHER_IS_BETTER:
        is_better = candidate_metric > production_metric
    else:
        is_better = candidate_metric < production_metric

    if not is_better:
        return False

    # Register candidate
    model_uri = f"runs:/{run_id}/model"
    result = mlflow.register_model(model_uri, model_name)

    # Move old production to Archived
    for version in client.get_latest_versions(model_name, stages=["Production"]):
        client.transition_model_version_stage(
            name=model_name,
            version=version.version,
            stage="Archived",
        )

    # Promote new version
    client.transition_model_version_stage(
        name=model_name,
        version=result.version,
        stage="Production",
    )

    return True



def get_production_model(
    model_name: str,
    alias: str = "prod",
) -> Optional[mlflow.entities.model_registry.ModelVersion]:
    """
    Retrieve the model version pointed to by the 'prod' alias
    (new MLflow UI).

    Args:
        model_name: registered model name
        alias: production alias (default: "prod")

    Returns:
        ModelVersion or None if no production model exists
    """
    client = MlflowClient()

    try:
        model_version = client.get_model_version_by_alias(
            name=model_name,
            alias=alias,
        )

        logging.info(
            "Production model found | name=%s | version=%s | run_id=%s",
            model_name,
            model_version.version,
            model_version.run_id,
        )

        return model_version

    except RestException:
        logging.warning(
            "No production model found for model=%s (alias=%s)",
            model_name,
            alias,
        )
        return None
