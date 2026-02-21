"""
MLflow Model Registry utilities.

Provides read access helpers for retrieving model versions
and production pointers from the MLflow Model Registry.

This module contains no business logic. It only wraps
MLflow client calls used by higher-level pipeline orchestration.
"""

import logging
from typing import Optional

import mlflow
from mlflow.tracking import MlflowClient
from mlflow.exceptions import RestException, MlflowException


def get_model_version_from_alias(
    model_name: str,
    alias: str,
) -> Optional[mlflow.entities.model_registry.ModelVersion]:
    """
    Retrieve the model version associated with a given alias.

    Args:
        model_name: Registered model name.
        alias: Alias name (e.g. "prod", "staging").

    Returns:
        ModelVersion if alias exists, otherwise None.
    """
    client = MlflowClient()

    try:
        model_version = client.get_model_version_by_alias(
            name=model_name,
            alias=alias,
        )

        logging.info(
            "Model alias found | name=%s | alias=%s | version=%s | run_id=%s",
            model_name,
            alias,
            model_version.version,
            model_version.run_id,
        )

        return model_version

    except RestException:
        logging.warning(
            "Alias not found | model=%s | alias=%s",
            model_name,
            alias,
        )
        return None


def get_production_model(
    model_name: str,
    alias: str = "prod",
) -> Optional[mlflow.entities.model_registry.ModelVersion]:
    """
    Retrieve the model version currently marked as production.

    Args:
        model_name: Registered model name.
        alias: Production alias (default: "prod").

    Returns:
        ModelVersion if a production model exists, otherwise None.
    """
    return get_model_version_from_alias(model_name, alias)


def get_production_run_id(model_name: str) -> Optional[str]:
    """
    Retrieve run_id of model aliased as 'prod'
    """
    client = MlflowClient()

    try:
        model_version = client.get_model_version_by_alias(
            model_name,
            "prod"
        )
    except MlflowException:
        return None

    return model_version.run_id
