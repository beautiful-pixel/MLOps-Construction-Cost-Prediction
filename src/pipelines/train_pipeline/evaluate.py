"""
Evaluation pipeline.

Load trained model from MLflow using run_id
and evaluate it on:

- Reference test dataset (official benchmark)
- Optional test datasets

Metrics are logged to the existing MLflow run.
"""
import os
from pathlib import Path
from typing import Dict
import logging
import time
import pandas as pd
import mlflow

from features.feature_schema import (
    extract_features_and_target,
    get_allowed_feature_versions,
)

from training.metrics import compute_metrics
from models.loader import load_model_from_run

logger = logging.getLogger(__name__)

DATA_ROOT = os.getenv("DATA_ROOT")
if not DATA_ROOT:
    raise RuntimeError("DATA_ROOT environment variable is not defined")

DATA_ROOT = Path(DATA_ROOT).resolve()
REFERENCE_ROOT = DATA_ROOT / "reference" / "tests"
SPLITS_ROOT = DATA_ROOT / "splits"


def evaluate_model(
    run_id: str,
    split_version: int,
    feature_version: int,
) -> Dict:

    start_time = time.time()

    logger.info(
        "Starting evaluation | "
        f"run_id={run_id}, "
        f"split_version={split_version}, "
        f"feature_version={feature_version}"
    )

    if feature_version not in get_allowed_feature_versions():
        raise ValueError(f"Invalid feature_version: {feature_version}")

    logger.info("Loading model from MLflow")
    pipeline = load_model_from_run(run_id=run_id)

    reference_path = (
        REFERENCE_ROOT / f"v{split_version}" / "test_reference.parquet"
    )

    if not reference_path.exists():
        raise ValueError(f"Reference test not found at {reference_path}")

    reference_df = pd.read_parquet(reference_path)
    logger.info(f"Reference dataset loaded ({len(reference_df)} rows)")

    metrics: Dict[str, float] = {}

    # Reference evaluation

    logger.info("Evaluating reference dataset")

    X_ref, y_ref = extract_features_and_target(
        reference_df,
        feature_version,
    )

    ref_predictions = pipeline.predict(X_ref)
    reference_metrics = compute_metrics(y_ref, ref_predictions)

    metrics.update({
        f"reference_{k}": v
        for k, v in reference_metrics.items()
    })

    logger.info(
        "Reference metrics | "
        + ", ".join(
            f"{k}={v:.4f}" for k, v in reference_metrics.items()
        )
    )

    # Optional tests

    optional_dir = (
        SPLITS_ROOT / f"v{split_version}" / "optional_tests"
    )

    if optional_dir.exists():
        logger.info("Evaluating optional test datasets")

        for test_path in optional_dir.glob("*.parquet"):

            name = test_path.stem
            test_df = pd.read_parquet(test_path)

            if test_df.empty:
                logger.warning(f"{name} is empty, skipping")
                continue

            logger.info(f"Evaluating optional test: {name}")

            X_opt, y_opt = extract_features_and_target(
                test_df,
                feature_version,
            )

            opt_predictions = pipeline.predict(X_opt)
            opt_metrics = compute_metrics(y_opt, opt_predictions)

            metrics.update({
                f"{name}_{k}": v
                for k, v in opt_metrics.items()
            })

            logger.info(
                f"{name} metrics | "
                + ", ".join(
                    f"{k}={v:.4f}" for k, v in opt_metrics.items()
                )
            )

    duration = round(time.time() - start_time, 2)
    metrics["evaluation_duration"] = duration

    logger.info(f"Evaluation completed in {duration}s")

    mlflow.start_run(run_id=run_id)
    try:
        mlflow.log_metrics(metrics)
    finally:
        mlflow.end_run()

    return metrics