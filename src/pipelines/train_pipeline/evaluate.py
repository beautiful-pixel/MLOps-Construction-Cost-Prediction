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


    # model_uri = f"runs:/{run_id}/model"
    # logging.info(f"Loading model from {model_uri}")
    # pipeline = mlflow.sklearn.load_model(model_uri)
    


    client = MlflowClient()
    run = client.get_run(run_id)

    artifact_uri = run.info.artifact_uri
    # exemple: file:///mlflow_server/artifacts/1/<run_id>/artifacts

    local_path = artifact_uri.replace("file://", "")
    model_path = Path(local_path) / "model"

    logging.info(f"Loading model from local path {model_path}")
    pipeline = mlflow.sklearn.load_model(str(model_path))

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
