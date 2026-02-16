"""
Data contract management utilities.

This module centralizes all logic related to versioned data contracts.

Responsibilities:

- Load a data contract by version
- Validate dataframe structure and constraints
- Enforce primary key integrity
- Expose deduplication rules

The data contract defines the structural integrity
of the master dataset and acts as the single source of truth
for schema validation.
"""

from pathlib import Path
from typing import Dict, List
import yaml
import pandas as pd
import re


# Paths

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_CONTRACT_DIR = PROJECT_ROOT / "configs" / "data_contracts"


from utils.versioned_config import load_versioned_yaml, get_available_versions



# Version utilities

def get_data_contract_versions() -> List[int]:
    """
    Return available data contract versions.
    """
    return get_available_versions("data_contracts")


# Loading

def load_data_contract(version: int) -> Dict:
    """
    Load a versioned data contract.
    """
    return load_versioned_yaml("data_contracts", version)

# Validation

def validate_dataframe(
    df: pd.DataFrame,
    data_contract_version: int,
    strict_columns: bool = True,
) -> None:
    """
    Validate a dataframe against a versioned data contract.

    Checks:
    - Column presence
    - Column constraints (type, range, format, allowed values)
    - Primary key integrity

    Raises an error if validation fails.
    """

    if df.empty:
        raise ValueError("Input dataframe is empty.")

    contract = load_data_contract(data_contract_version)

    _validate_columns(df, contract, strict_columns)
    _validate_column_constraints(df, contract)
    _validate_primary_key(df, contract)


def _validate_columns(
    df: pd.DataFrame,
    contract: Dict,
    strict_columns: bool,
) -> None:
    """Validate required and unexpected columns."""

    expected = set(contract["columns"].keys())
    actual = set(df.columns)

    missing = expected - actual
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    if strict_columns:
        unexpected = actual - expected
        if unexpected:
            raise ValueError(f"Unexpected columns present: {unexpected}")


def _validate_column_constraints(
    df: pd.DataFrame,
    contract: Dict,
) -> None:
    """Validate column constraints defined in the contract."""

    for col, rules in contract["columns"].items():

        series = df[col]

        # Non-nullable
        if rules.get("non_nullable", False):
            if series.isna().any():
                raise ValueError(f"Column '{col}' contains null values.")

        # Type
        _validate_type(col, series, rules)

        # Min / Max
        if "min" in rules:
            if (series.dropna() < rules["min"]).any():
                raise ValueError(
                    f"Column '{col}' contains values below min {rules['min']}"
                )

        if "max" in rules:
            if (series.dropna() > rules["max"]).any():
                raise ValueError(
                    f"Column '{col}' contains values above max {rules['max']}"
                )

        # Allowed values
        if "allowed_values" in rules:
            allowed = set(rules["allowed_values"])
            invalid = set(series.dropna().unique()) - allowed
            if invalid:
                raise ValueError(
                    f"Column '{col}' contains invalid values: {invalid}"
                )

        # Regex
        if "format" in rules:
            pattern = re.compile(rules["format"])
            invalid_mask = series.dropna().astype(str).apply(
                lambda x: not bool(pattern.fullmatch(x))
            )
            if invalid_mask.any():
                raise ValueError(
                    f"Column '{col}' contains values not matching regex."
                )


def _validate_primary_key(
    df: pd.DataFrame,
    contract: Dict,
) -> None:
    """Validate primary key integrity."""

    primary_key = contract.get("primary_key")

    if not primary_key:
        return

    if df[primary_key].isna().any().any():
        raise ValueError(
            f"Primary key columns {primary_key} contain null values."
        )

    duplicates = df.duplicated(subset=primary_key, keep=False)

    if duplicates.any():
        duplicated_rows = df.loc[duplicates, primary_key]
        raise ValueError(
            "Primary key constraint violated. "
            f"Duplicate values found:\n{duplicated_rows}"
        )


def _validate_type(
    col: str,
    series: pd.Series,
    rules: Dict,
) -> None:
    """Validate column dtype against contract specification."""

    expected_type = rules.get("type")

    if expected_type == "int":
        if not pd.api.types.is_integer_dtype(series):
            raise TypeError(f"Column '{col}' must be integer.")

    elif expected_type == "float":
        if not pd.api.types.is_float_dtype(series):
            raise TypeError(f"Column '{col}' must be float.")

    elif expected_type == "string":
        if not pd.api.types.is_string_dtype(series):
            raise TypeError(f"Column '{col}' must be string.")

    else:
        raise ValueError(f"Unsupported type '{expected_type}' in contract.")


# Access helpers

def get_primary_key(version: int) -> List[str]:
    """
    Return primary key columns for a given contract version.
    """
    contract = load_data_contract(version)
    return contract.get("primary_key", [])


def get_deduplication_rules(version: int) -> Dict:
    """
    Return deduplication configuration for a given version.
    """
    contract = load_data_contract(version)
    return contract.get("deduplication", {})
