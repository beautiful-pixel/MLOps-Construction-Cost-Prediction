"""
Training pipeline.

Build and fit a full sklearn pipeline composed of:

- A versioned feature preprocessor
- A versioned model definition

This module:
- Reloads persisted train split
- Validates dataset against feature schema
- Fits pipeline
- Logs artifacts and metrics to an existing MLflow run
"""
import os
from pathlib import Path
import os
import logging
import time
import pandas as pd
import mlflow
import mlflow.sklearn

from sklearn.pipeline import Pipeline

from splitting.split_schema import get_allowed_split_versions
from features.feature_schema import (
    get_allowed_feature_versions,
    extract_features_and_target,
    validate_dataframe,
    load_feature_schema,
)
from features.model_preprocessor import build_tabular_model_preprocessor
from models.model_schema import (
    get_allowed_model_versions,
    build_model,
    load_model_schema,
)
from training.metrics import compute_metrics


# Logger

logger = logging.getLogger(__name__)


# Paths

DATA_ROOT = os.getenv("DATA_ROOT")
if not DATA_ROOT:
    raise RuntimeError("DATA_ROOT environment variable is not defined")

DATA_ROOT = Path(DATA_ROOT).resolve()
SPLITS_ROOT = DATA_ROOT / "splits"


def train_model(
    run_id: str,
    split_version: int,
    feature_version: int,
    model_version: int,
) -> dict:
    """
    Train model using persisted split and log results
    to an existing MLflow run.
    """

    start_time = time.time()

    logger.info(
        "Starting training | "
        f"run_id={run_id}, "
        f"split_version={split_version}, "
        f"feature_version={feature_version}, "
        f"model_version={model_version}"
    )

    # Validate versions

    if split_version not in get_allowed_split_versions():
        raise ValueError(f"Invalid split_version: {split_version}")

    if feature_version not in get_allowed_feature_versions():
        raise ValueError(f"Invalid feature_version: {feature_version}")

    if model_version not in get_allowed_model_versions():
        raise ValueError(f"Invalid model_version: {model_version}")

    # Load schemas

    feature_schema = load_feature_schema(feature_version)
    model_schema = load_model_schema(model_version)

    if feature_schema.get("image_features"):
        raise NotImplementedError(
            "Image features are defined in the feature schema but are not "
            "supported by the current training pipeline."
        )

    # Load persisted train split

    train_path = SPLITS_ROOT / f"v{split_version}" / "train.parquet"

    if not train_path.exists():
        raise ValueError(f"Train split not found at {train_path}")

    logger.info(f"Loading train split from {train_path}")
    train_df = pd.read_parquet(train_path)

    n_rows = len(train_df)
    logger.info(f"Training dataset loaded ({n_rows} rows)")

    # Validate dataset

    validate_dataframe(train_df, feature_version)
    X, y = extract_features_and_target(train_df, feature_version)

    # Build pipeline
    logger.info("Building model")

    preprocessor = build_tabular_model_preprocessor(feature_schema)
    model = build_model(model_version)

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", model),
        ]
    )

    logger.info("Fitting training pipeline")
    pipeline.fit(X, y)

    logger.info("Train prediction")
    predictions = pipeline.predict(X)

    metrics = compute_metrics(y, predictions)
    metrics = {f"train_{k}": v for k, v in metrics.items()}

    params = {
        "model_type": model_schema["model"]["type"],
        **model_schema["model"].get("params", {}),
    }

    duration = round(time.time() - start_time, 2)
    metrics['training_duration'] = duration

    logger.info(f"Training completed in {duration}s")

    mlflow.start_run(run_id=run_id)

    try:
        mlflow.log_params(params)
        mlflow.log_metrics(metrics)
        mlflow.sklearn.log_model(pipeline, artifact_path="model")

    finally:
        mlflow.end_run()

    return metrics