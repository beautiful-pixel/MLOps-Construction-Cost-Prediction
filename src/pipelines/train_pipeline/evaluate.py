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

SHARED_ARTIFACTS_ROOT = Path("/mlflow_artifacts")


def _load_model(run_id: str):
    """
    Load model from shared artifact volume (fast path).
    Falls back to MLflow client download if local path is unavailable.
    """
    client = MlflowClient()
    run = client.get_run(run_id)
    artifact_uri = run.info.artifact_uri

    # Fast path: resolve from shared Docker volume
    # artifact_uri looks like /mlflow_artifacts/<experiment_id>/<run_id>/artifacts
    if SHARED_ARTIFACTS_ROOT.exists():
        # Strip scheme if present
        raw = artifact_uri.replace("mlflow-artifacts:", "").replace("file://", "")
        # Normalize: ensure path starts from the shared root
        if raw.startswith("/mlflow_artifacts"):
            local_path = Path(raw) / "model"
        else:
            # Try to reconstruct from run info
            local_path = (
                SHARED_ARTIFACTS_ROOT
                / str(run.info.experiment_id)
                / run_id
                / "artifacts"
                / "model"
            )

        if local_path.exists():
            logging.info("Loading model from shared volume: %s", local_path)
            return mlflow.sklearn.load_model(str(local_path))

    # Fallback: download through MLflow tracking server
    logging.info("Shared volume path unavailable, loading via MLflow client")
    model_uri = f"runs:/{run_id}/model"
    return mlflow.sklearn.load_model(model_uri)


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

    pipeline = _load_model(run_id)

    # Load reference test

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
