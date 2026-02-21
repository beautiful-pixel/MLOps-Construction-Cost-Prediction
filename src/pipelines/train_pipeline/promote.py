"""
Model promotion logic.

Compare a candidate run against the current production model
based on reference test metrics.

Promote candidate if it performs better.
"""

import logging
from typing import Optional, Dict

import mlflow
from mlflow.tracking import MlflowClient

from utils.mlflow_config import get_model_name
from registry.run_metadata import get_run_metric
from registry.model_registry import get_model_version_from_alias


REFERENCE_METRIC = "reference_rmsle"
HIGHER_IS_BETTER = False  # False for loss-like metrics


logger = logging.getLogger(__name__)


def _is_better(new: float, old: Optional[float]) -> bool:
    if old is None:
        return True
    if HIGHER_IS_BETTER:
        return new > old
    return new < old


def promote_if_better(run_id: str) -> Dict:
    """
    Promote a candidate run to production if it outperforms
    the currently promoted model.

    Returns:
        Dict containing:
            - promoted (bool)
            - candidate_metric (float)
            - production_metric (Optional[float])
            - metric_name (str)
            - new_model_version (Optional[int])
    """

    model_name = get_model_name()
    client = MlflowClient()

    # Candidate metric
    candidate_metric = get_run_metric(run_id, REFERENCE_METRIC)

    if candidate_metric is None:
        raise ValueError(
            f"Metric '{REFERENCE_METRIC}' not found in run {run_id}"
        )

    logger.info(
        "Candidate metric | run_id=%s | %s=%s",
        run_id,
        REFERENCE_METRIC,
        candidate_metric,
    )

    # Current production
    prod_version = get_model_version_from_alias(model_name, "prod")
    production_metric: Optional[float] = None
    production_run_id: Optional[str] = None

    if prod_version is not None:
        production_run_id = prod_version.run_id
        production_metric = get_run_metric(
            production_run_id,
            REFERENCE_METRIC,
        )

        logger.info(
            "Production metric | run_id=%s | %s=%s",
            production_run_id,
            REFERENCE_METRIC,
            production_metric,
        )

    # Compare
    promoted = _is_better(candidate_metric, production_metric)

    if not promoted:
        logger.info("Candidate model not promoted (no improvement).")

        return {
            "promoted": False,
            "candidate_metric": candidate_metric,
            "production_metric": production_metric,
            "metric_name": REFERENCE_METRIC,
            "new_model_version": None,
        }

    # Register new model version
    model_uri = f"runs:/{run_id}/model"
    result = mlflow.register_model(model_uri, model_name)

    logger.info(
        "Model registered | name=%s | version=%s",
        model_name,
        result.version,
    )

    # Update alias
    client.set_registered_model_alias(
        name=model_name,
        alias="prod",
        version=result.version,
    )

    logger.info(
        "Alias updated | model=%s | alias=prod | version=%s",
        model_name,
        result.version,
    )

    return {
        "promoted": True,
        "candidate_metric": candidate_metric,
        "production_metric": production_metric,
        "metric_name": REFERENCE_METRIC,
        "new_model_version": result.version,
    }