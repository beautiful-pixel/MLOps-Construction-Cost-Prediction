"""
Model promotion logic.

Compare a candidate run against the current production model
based on reference test metrics.

Promote candidate if it performs better.
"""

import logging
from typing import Optional

import mlflow
from mlflow.tracking import MlflowClient

from utils.mlflow_config import get_model_name
from registry.run_metadata import get_run_metric
from registry.model_registry import get_model_version_from_alias


REFERENCE_METRIC = "reference_rmsle"
HIGHER_IS_BETTER = False  # False for loss-like metrics


def _is_better(new: float, old: Optional[float]) -> bool:
    if old is None:
        return True
    if HIGHER_IS_BETTER:
        return new > old
    return new < old


def promote_if_better(run_id: str) -> bool:
    """
    Promote a candidate run to production if it outperforms
    the currently promoted model.

    Args:
        run_id: Candidate MLflow run ID.

    Returns:
        True if promoted, False otherwise.
    """

    model_name = get_model_name()
    
    client = MlflowClient()

    # Retrieve candidate metric
    candidate_metric = get_run_metric(run_id, REFERENCE_METRIC)

    if candidate_metric is None:
        raise ValueError(
            f"Metric '{REFERENCE_METRIC}' not found in run {run_id}"
        )

    logging.info(
        "Candidate metric | run_id=%s | %s=%s",
        run_id,
        REFERENCE_METRIC,
        candidate_metric,
    )

    # Retrieve current production model via alias
    prod_version = get_model_version_from_alias(model_name, "prod")

    production_metric: Optional[float] = None

    if prod_version is not None:
        production_metric = get_run_metric(
            prod_version.run_id,
            REFERENCE_METRIC,
        )

        logging.info(
            "Current production metric | run_id=%s | %s=%s",
            prod_version.run_id,
            REFERENCE_METRIC,
            production_metric,
        )

    # Compare metrics
    if not _is_better(candidate_metric, production_metric):
        logging.info("Candidate model not promoted (no improvement).")
        return False

    # Register model version
    model_uri = f"runs:/{run_id}/model"
    result = mlflow.register_model(model_uri, model_name)

    logging.info(
        "Model registered | name=%s | version=%s",
        model_name,
        result.version,
    )

    # Update alias to point to new version
    client.set_registered_model_alias(
        name=model_name,
        alias="prod",
        version=result.version,
    )

    logging.info(
        "Alias updated | model=%s | alias=prod | version=%s",
        model_name,
        result.version,
    )

    return True
