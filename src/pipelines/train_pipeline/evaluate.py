"""
Evaluation pipeline.

Load trained model from MLflow using run_id
and evaluate it on:

- Reference test dataset (official benchmark)
- Optional test datasets

Metrics are logged to the existing MLflow run.
"""

from mlflow.tracking import MlflowClient
from pathlib import Path
from typing import Dict
import logging
import pandas as pd
import mlflow
import mlflow.sklearn

from features.feature_schema import (
    extract_features_and_target,
    get_allowed_feature_versions,
)

from training.metrics import compute_metrics


# Paths

PROJECT_ROOT = Path(__file__).resolve().parents[3]
REFERENCE_ROOT = PROJECT_ROOT / "data" / "reference" / "tests"
SPLITS_ROOT = PROJECT_ROOT / "data" / "splits"





MLFLOW_ROOT = PROJECT_ROOT / "mlflow_server" / "artifacts"


def load_model_from_run(
    run_id: str,
    local_mode: bool = False,
):
    """
    Load a sklearn model from an MLflow run.

    If local_mode is False:
        Uses standard MLflow URI resolution (runs:/).

    If local_mode is True:
        Resolves model_id from MLflow metadata and loads
        directly from local filesystem, bypassing artifact API.
    """

    if not local_mode:
        model_uri = f"runs:/{run_id}/model"
        logging.info(f"Loading model via MLflow URI: {model_uri}")
        return mlflow.sklearn.load_model(model_uri)

    logging.info("Loading model in LOCAL mode (filesystem bypass)")

    client = MlflowClient()

    # Get run to retrieve experiment_id
    run = client.get_run(run_id)
    experiment_id = run.info.experiment_id

    # Search logged models linked to this run
    logged_models = client.search_logged_models(
        experiment_ids=[experiment_id],
        filter_string=f"source_run_id = '{run_id}'"
    )

    if not logged_models:
        raise ValueError(f"No logged model found for run_id={run_id}")

    model_id = logged_models[0].model_id

    model_path = (
        MLFLOW_ROOT
        / experiment_id
        / "models"
        / model_id
        / "artifacts"
    )

    if not model_path.exists():
        raise ValueError(f"Local model path not found: {model_path}")

    logging.info(f"Loading model from local path: {model_path}")

    return mlflow.sklearn.load_model(str(model_path))

    

def evaluate_model(
    run_id: str,
    split_version: int,
    feature_version: int,
) -> None:
    """
    Evaluate trained model using persisted test datasets
    and log metrics to existing MLflow run.

    Args:
        run_id (str):
            Active MLflow run ID.
        split_version (int):
            Split version used during training.
        feature_version (int):
            Feature schema version.
    """

    if feature_version not in get_allowed_feature_versions():
        raise ValueError(f"Invalid feature_version: {feature_version}")

    # Load model from MLflow

    pipeline = load_model_from_run(
        run_id=run_id,
        local_mode=True,   # False en prod
    )


    # Load reference test

    reference_path = (
        REFERENCE_ROOT / f"v{split_version}" / "test_reference.parquet"
    )

    if not reference_path.exists():
        raise ValueError(f"Reference test not found at {reference_path}")

    reference_df = pd.read_parquet(reference_path)

    # Attach to existing MLflow run

    mlflow.start_run(run_id=run_id)

    # Reference evaluation

    X_ref, y_ref = extract_features_and_target(
        reference_df,
        feature_version,
    )

    ref_predictions = pipeline.predict(X_ref)
    reference_metrics = compute_metrics(y_ref, ref_predictions)

    mlflow.log_metrics(
        {f"reference_{k}": v for k, v in reference_metrics.items()}
    )

    # Optional tests

    optional_dir = (
        SPLITS_ROOT / f"v{split_version}" / "optional_tests"
    )

    if optional_dir.exists():

        for test_path in optional_dir.glob("*.parquet"):

            name = test_path.stem
            test_df = pd.read_parquet(test_path)

            if test_df.empty:
                continue

            X_opt, y_opt = extract_features_and_target(
                test_df,
                feature_version,
            )

            opt_predictions = pipeline.predict(X_opt)
            opt_metrics = compute_metrics(y_opt, opt_predictions)

            mlflow.log_metrics(
                {f"{name}_{k}": v for k, v in opt_metrics.items()}
            )

    logging.info("Evaluation completed successfully")
