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
import os
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
from models.loader import load_model_from_run


# Paths

PROJECT_ROOT_ENV = os.getenv("PROJECT_ROOT")
if not PROJECT_ROOT_ENV:
    raise RuntimeError("PROJECT_ROOT env var is required")
PROJECT_ROOT = Path(PROJECT_ROOT_ENV)
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

    # Load model and reference test

    pipeline = load_model_from_run(run_id=run_id)

    reference_path = (
        REFERENCE_ROOT / f"v{split_version}" / "test_reference.parquet"
    )

    if not reference_path.exists():
        raise ValueError(f"Reference test not found at {reference_path}")

    reference_df = pd.read_parquet(reference_path)

    # Attach to existing MLflow run

    mlflow.start_run(run_id=run_id)

    try:
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

    finally:
        mlflow.end_run()

    logging.info("Evaluation completed successfully")
