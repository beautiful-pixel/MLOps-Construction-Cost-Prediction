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

from pathlib import Path
import logging
import pandas as pd
import mlflow
import mlflow.sklearn

from sklearn.pipeline import Pipeline

from splitting.split_schema import get_allowed_versions as get_allowed_split_versions
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


# Paths

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SPLITS_ROOT = PROJECT_ROOT / "data" / "splits"


def train_model(
    run_id: str,
    split_version: int,
    feature_version: int,
    model_version: int,
) -> None:
    """
    Train model using persisted split and log results
    to an existing MLflow run.

    Args:
        run_id (str):
            Active MLflow run ID.
        split_version (int):
            Validated split version.
        feature_version (int):
            Validated feature schema version.
        model_version (int):
            Validated model schema version.
    """

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


    # Load persisted train split

    train_path = SPLITS_ROOT / f"v{split_version}" / "train.parquet"

    if not train_path.exists():
        raise ValueError(f"Train split not found at {train_path}")

    logging.info(f"Loading train split from {train_path}")
    train_df = pd.read_parquet(train_path)

    # Validate dataset

    validate_dataframe(train_df, feature_version)
    X, y = extract_features_and_target(train_df, feature_version)


    # Build pipeline

    preprocessor = build_tabular_model_preprocessor(feature_schema)
    model = build_model(model_version)

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", model),
        ]
    )


    # Attach to existing MLflow run
    mlflow.start_run(run_id=run_id)

    # Log versions (redundant but safe)
    mlflow.log_param("split_version", split_version)
    mlflow.log_param("feature_version", feature_version)
    mlflow.log_param("model_version", model_version)

    mlflow.log_param("model_type", model_schema["model"]["type"])
    mlflow.log_params(model_schema["model"].get("params", {}))


    # Train

    logging.info("Fitting training pipeline")
    pipeline.fit(X, y)

    predictions = pipeline.predict(X)
    train_metrics = compute_metrics(y, predictions)
    train_metrics = {f"train_{k}": v for k, v in train_metrics.items()}

    mlflow.log_metrics(train_metrics)


    # Log model artifact
    
    mlflow.sklearn.log_model(pipeline, artifact_path="model")

    logging.info("Training completed successfully")
