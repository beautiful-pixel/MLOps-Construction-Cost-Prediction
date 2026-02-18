"""
MLflow model loading utilities.

Provides helpers to load models from:
- a run ID
- a specific model version
- a model alias (e.g. "prod")
"""

import logging
from typing import Any, Optional

import mlflow


def load_model_from_run(run_id: str) -> Any:
    """
    Load a model artifact from a specific MLflow run.
    """
    model_uri = f"runs:/{run_id}/model"
    logging.info("Loading model from run | uri=%s", model_uri)
    return mlflow.pyfunc.load_model(model_uri)


def load_model_version(
    model_name: str,
    version: int,
) -> Any:
    """
    Load a specific version of a registered model.
    """
    model_uri = f"models:/{model_name}/{version}"
    logging.info(
        "Loading model from registry | name=%s | version=%s",
        model_name,
        version,
    )
    return mlflow.pyfunc.load_model(model_uri)


def load_model_by_alias(
    model_name: str,
    alias: str = "prod",
) -> Any:
    """
    Load a model from a registry alias (e.g. 'prod').
    """
    model_uri = f"models:/{model_name}@{alias}"
    logging.info(
        "Loading model from registry | name=%s | alias=%s",
        model_name,
        alias,
    )
    return mlflow.pyfunc.load_model(model_uri)


def load_production_model(
    model_name: str,
    version: Optional[int] = None,
) -> Any:
    """
    Load the production model.

    If version is provided:
        Loads that specific version.
    Otherwise:
        Loads the model pointed to by alias 'prod'.
    """
    if version is not None:
        return load_model_version(model_name, version)

    return load_model_by_alias(model_name, alias="prod")
