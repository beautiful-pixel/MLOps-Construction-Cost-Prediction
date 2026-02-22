"""
Feature schema management utilities.

This module centralizes everything related to
versioned feature configurations:

- Loading feature schema by version
- Extracting feature columns
- Validating dataframe structure and content
- Extracting X and y for modeling

Feature schema references a data contract.
Target is defined in the data contract.
"""

from typing import Tuple, List, Dict
import pandas as pd

from utils.versioned_config import load_versioned_yaml, get_available_versions
from data.data_contract import get_target_column, load_data_contract


# Version utilities

def get_allowed_feature_versions() -> List[int]:
    """
    Return available feature schema versions.
    """
    return get_available_versions("features")


def get_feature_versions_for_contract(contract_version: int) -> List[int]:
    """
    Return feature versions attached to a given data contract version.
    """

    versions = get_allowed_feature_versions()
    valid_versions = []

    for v in versions:
        schema = load_feature_schema(v)

        if schema.get("data_contract") == contract_version:
            valid_versions.append(v)

    return sorted(valid_versions)

def get_next_feature_version() -> int:
    """
    Return next feature version number (incremental).
    """

    versions = get_allowed_feature_versions()

    if not versions:
        return 1

    return max(versions) + 1

# Loading

def load_feature_schema(version: int) -> Dict:
    """
    Load feature configuration by version.
    """
    return load_versioned_yaml("features", version)


# Helpers

def get_feature_columns(schema: dict) -> List[str]:
    """
    Return ordered tabular feature columns.
    """
    return list(schema.get("tabular_features", {}).keys())


def get_required_columns(schema: dict) -> List[str]:
    """
    Return required columns including features,
    optional split columns, and target.
    """
    contract_version = schema["data_contract"]
    target = [get_target_column(contract_version)]
    split = schema.get("split_columns", [])

    return get_feature_columns(schema) + split + target


def get_ordered_features(version: int) -> List[str]:
    """
    Return ordered features (tabular + image).
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

    if df.empty:
        raise ValueError("Input dataframe is empty.")

    schema = load_feature_schema(version)

    # Validate contract consistency
    _validate_feature_contract_consistency(schema)

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


def _validate_feature_contract_consistency(schema: dict) -> None:
    """
    Ensure feature schema is consistent with referenced data contract.
    """

    contract_version = schema.get("data_contract")

    if contract_version is None:
        raise ValueError("Feature schema must define 'data_contract'.")

    contract = load_data_contract(contract_version)

    contract_columns = set(contract["columns"].keys())
    feature_columns = set(schema.get("tabular_features", {}).keys())

    invalid = feature_columns - contract_columns

    if invalid:
        raise ValueError(
            f"Feature schema references columns not in data contract: {invalid}"
        )


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

            if "impute" not in params and df[col].isna().any() or df[col].isin([None]).any():
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
    Target is loaded from the referenced data contract.
    """

    if df.empty:
        raise ValueError("Input dataframe is empty.")

    schema = load_feature_schema(version)

    contract_version = schema["data_contract"]
    target_col = get_target_column(contract_version)

    feature_cols = get_feature_columns(schema)

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


# Schema definition validation
def validate_feature_schema_definition(schema: Dict) -> None:
    """
    Validate structure and integrity of a feature schema definition.

    Used when creating a new feature version via API.

    Rules enforced:
    - All features must exist in referenced data contract
    - Feature types must be valid
    - Categorical encodings must be valid
    - Ordinal features must define an order
    - If a column is nullable in data contract, an imputation strategy is mandatory
    - Target must not be defined here (comes from data contract)
    """

    # Required top-level keys
    required_keys = {"version", "data_contract", "tabular_features"}

    missing = required_keys - set(schema.keys())
    if missing:
        raise ValueError(
            f"Missing required keys in feature schema: {missing}"
        )

    # Validate data contract exists
    contract_version = schema["data_contract"]

    try:
        contract = load_data_contract(contract_version)
    except Exception:
        raise ValueError(
            f"Referenced data_contract v{contract_version} does not exist."
        )

    contract_columns = contract["columns"]

    tabular_features = schema.get("tabular_features", {})

    if not tabular_features:
        raise ValueError(
            "Feature schema must define at least one tabular feature."
        )

    allowed_feature_types = {"numeric", "categorical"}
    allowed_encodings = {"binary", "ordinal", "onehot"}
    allowed_imputers = {"mean", "median", "most_frequent", "constant"}

    for col, params in tabular_features.items():

        # Column must exist in data contract
        if col not in contract_columns:
            raise ValueError(
                f"Feature '{col}' not found in data contract."
            )

        contract_col = contract_columns[col]

        # Feature type validation
        feature_type = params.get("type")
        if feature_type not in allowed_feature_types:
            raise ValueError(
                f"Feature '{col}' has invalid type '{feature_type}'. "
                f"Allowed types: {allowed_feature_types}"
            )

        # Nullable rule enforcement
        is_nullable = not contract_col.get("non_nullable", False)

        if is_nullable and "impute" not in params:
            raise ValueError(
                f"Feature '{col}' is nullable in data contract and "
                f"must define an 'impute' strategy."
            )

        # Validate imputation strategy if defined
        if "impute" in params:
            if params["impute"] not in allowed_imputers:
                raise ValueError(
                    f"Feature '{col}' has invalid imputation strategy "
                    f"'{params['impute']}'. "
                    f"Allowed strategies: {allowed_imputers}"
                )

        # Numeric-specific rules
        if feature_type == "numeric":
            # Nothing else mandatory beyond nullable rule
            pass

        # Categorical-specific rules
        if feature_type == "categorical":

            encoding = params.get("encoding")
            if encoding not in allowed_encodings:
                raise ValueError(
                    f"Feature '{col}' has invalid encoding '{encoding}'. "
                    f"Allowed encodings: {allowed_encodings}"
                )

            if encoding == "ordinal":
                if "order" not in params:
                    raise ValueError(
                        f"Ordinal feature '{col}' must define 'order'."
                    )

                if not isinstance(params["order"], list):
                    raise ValueError(
                        f"'order' for feature '{col}' must be a list."
                    )

    # Ensure target is not defined in feature schema
    if "target" in schema:
        raise ValueError(
            "Feature schema must not define 'target'. "
            "Target is defined in the data contract."
        )