"""
Feature schema management utilities.

This module centralizes everything related to
versioned feature configurations:

- Loading feature schema by version
- Extracting feature columns
- Validating dataframe structure and content
- Extracting X and y for modeling

Tabular features only (v1).
"""

from pathlib import Path
from typing import Tuple, List, Dict
import pandas as pd

from utils.versioned_config import load_versioned_yaml, get_available_versions

# Paths

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FEATURE_CONFIG_DIR = PROJECT_ROOT / "configs" / "features"


# Version utilities

def get_allowed_feature_versions() -> List[int]:
    """
    Return available feature schema versions.
    """
    return get_available_versions("features")


# Loading

def load_feature_schema(version: int) -> Dict:
    """
    Load feature configuration by version.
    """
    return load_versioned_yaml("features", version)


# Helpers

def get_feature_columns(schema: dict) -> List[str]:
    """
    Return ordered tabular feature columns (excluding target).
    """
    return list(schema.get("tabular_features", {}).keys())


def get_required_columns(schema: dict) -> List[str]:
    """
    Return all required columns including target and optional split columns.
    """
    target = [schema["target"]]
    split = schema.get("split_columns", [])

    return get_feature_columns(schema) + split + target

def get_ordered_features(version: int) -> List[str]:
    """
    Return ordered feature
    """
    schema = load_feature_schema(version)

    tabular_features = list(
        schema.get("tabular_features", {}).keys()
    )
    image_features = list(
        schema.get("image_features", {}).keys()
    )
    ordered_features = tabular_features + image_features

    if not ordered_features:
        raise ValueError(
            f"No features found in feature schema v{version}"
        )

    return ordered_features


# Validation

def validate_dataframe(
    df: pd.DataFrame,
    version: int,
    strict_columns: bool = False,
) -> None:
    """
    Validate dataframe against a versioned feature schema.
    """

    schema = load_feature_schema(version)

    required = set(get_required_columns(schema))
    actual = set(df.columns)

    missing = required - actual
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    if strict_columns:
        unexpected = actual - required
        if unexpected:
            raise ValueError(f"Unexpected columns present: {unexpected}")

    _validate_tabular_features(df, schema)


def _validate_tabular_features(df: pd.DataFrame, schema: dict) -> None:
    """
    Validate tabular features based on type and encoding.
    """

    tabular_cfg = schema.get("tabular_features", {})

    allowed_encodings = {"binary", "ordinal", "onehot"}

    for col, params in tabular_cfg.items():

        feature_type = params.get("type")

        if feature_type == "numeric":

            if not pd.api.types.is_numeric_dtype(df[col]):
                raise TypeError(f"Column '{col}' must be numeric.")

            if "impute" not in params and df[col].isna().any():
                raise ValueError(
                    f"Column '{col}' contains NaN but no imputation configured."
                )

        elif feature_type == "categorical":

            if "encoding" not in params:
                raise ValueError(
                    f"Categorical feature '{col}' must define an 'encoding'."
                )

            encoding = params["encoding"]

            if encoding not in allowed_encodings:
                raise ValueError(
                    f"Unsupported encoding '{encoding}' for column '{col}'. "
                    f"Allowed encodings: {allowed_encodings}"
                )

            # Validate allowed values if order is provided
            if encoding == "ordinal":
                if "order" not in params:
                    raise ValueError(
                        f"Ordinal feature '{col}' must define an 'order'."
                    )

                allowed = set(params["order"])
                invalid = set(df[col].dropna().unique()) - allowed

                if invalid:
                    raise ValueError(
                        f"Column '{col}' contains invalid ordinal values: {invalid}"
                    )

            # Optional: strict binary validation if order provided
            if encoding == "binary" and "order" in params:
                allowed = set(params["order"])
                invalid = set(df[col].dropna().unique()) - allowed

                if invalid:
                    raise ValueError(
                        f"Column '{col}' contains invalid binary values: {invalid}"
                    )

            if "impute" not in params and df[col].isna().any():
                raise ValueError(
                    f"Column '{col}' contains NaN but no imputation configured."
                )

        else:
            raise ValueError(
                f"Unsupported feature type '{feature_type}' for column '{col}'."
            )


# Extraction

def extract_features_and_target(
    df: pd.DataFrame,
    version: int,
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Extract X and y using a versioned feature schema.
    """

    if df.empty:
        raise ValueError("Input dataframe is empty.")

    schema = load_feature_schema(version)

    feature_cols = get_feature_columns(schema)
    target_col = schema["target"]

    missing_features = set(feature_cols) - set(df.columns)
    if missing_features:
        raise ValueError(f"Missing features in dataframe: {missing_features}")

    if target_col not in df.columns:
        raise ValueError(
            f"Target column '{target_col}' not found in dataframe."
        )

    X = df[feature_cols]
    y = df[target_col]

    return X, y
