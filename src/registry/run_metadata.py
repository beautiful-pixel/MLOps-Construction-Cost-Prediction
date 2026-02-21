"""
MLflow run metadata utilities.

Provides structured access to metrics, parameters and tags
stored in MLflow runs.

This module centralizes read-only interactions with MLflow
tracking for downstream evaluation and promotion logic.
"""

from typing import Dict, Optional

from mlflow.tracking import MlflowClient



def get_run_metrics(run_id: str) -> Dict[str, float]:
    """Return all logged metrics for a run."""
    client = MlflowClient()
    run = client.get_run(run_id)
    return dict(run.data.metrics)


def get_run_params(run_id: str) -> Dict[str, str]:
    """Return all logged parameters for a run."""
    client = MlflowClient()
    run = client.get_run(run_id)
    return dict(run.data.params)


def get_run_tags(run_id: str) -> Dict[str, str]:
    """Return all logged tags for a run."""
    client = MlflowClient()
    run = client.get_run(run_id)
    return dict(run.data.tags)


def get_run_metric(run_id: str, metric_name: str) -> Optional[float]:
    """Return a specific metric from a run."""
    metrics = get_run_metrics(run_id)
    return metrics.get(metric_name)


def get_run_config(run_id: str) -> Dict[str, int]:
    """
    Extract structured configuration from run parameters.

    Expected parameters:
        - split_version
        - feature_version
        - model_version
    """
    params = get_run_params(run_id)

    try:
        return {
            "split_version": int(params["split_version"]),
            "feature_version": int(params["feature_version"]),
            "model_version": int(params["model_version"]),
        }
    except KeyError as e:
        raise ValueError(
            f"Missing expected configuration parameter: {e}"
        ) from e
