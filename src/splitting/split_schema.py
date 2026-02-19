"""
Split schema management utilities.

This module centralizes everything related to
versioned dataset splitting strategies.

It is responsible for:

- Loading split configuration by version
- Validating configuration consistency
- Dispatching to the appropriate split strategy
- Generating train and named test splits

All functions operate from a split version integer (e.g. 1).

This ensures:

- Reproducible dataset splitting
- Explicit and versioned evaluation strategies
- Clean separation between split configuration and split logic
- Consistency across experiments
- Frozen static test sets when required
"""


from pathlib import Path
from typing import Tuple, Dict, List
import yaml
import pandas as pd

from utils.versioned_config import load_versioned_yaml, get_available_versions
from .split_strategies import geographic_split


# Version utilities

def get_allowed_split_versions() -> List[int]:
    """
    Return available split schema versions.
    Example:
        [1, 2]
    """
    return get_available_versions("splits")

def get_split_versions_for_contract(contract_version: int) -> list[int]:
    """
    Return split versions attached to a given data contract version.
    """

    versions = get_allowed_split_versions()
    valid_versions = []

    for v in versions:
        schema = load_split_schema(v)

        if schema.get("data_contract") == contract_version:
            valid_versions.append(v)

    return sorted(valid_versions)


# Loading

def load_split_schema(version: int) -> Dict:
    """
    Load split configuration by version (e.g. 1 -> v1.yaml).
    """
    return load_versioned_yaml("splits", version)


# Split dispatcher


def generate_split(
    df: pd.DataFrame,
    version: int,
) -> Tuple[
    pd.DataFrame,
    pd.DataFrame,
    Dict[str, pd.DataFrame],
]:
    """
    Generate dataset splits according to a versioned split configuration.

    The function dispatches to the configured split strategy and
    returns:

        - A training dataset
        - A mandatory reference test dataset (frozen)
        - A dictionary of additional test datasets

    Args:
        df (pd.DataFrame): Master dataset.
        version (int): Split configuration version.

    Returns:
        Tuple[
            pd.DataFrame,
            pd.DataFrame,
            Dict[str, pd.DataFrame]
        ]:
            train_df:
                Training dataset.

            test_reference_df:
                Mandatory reference test dataset
                (typically frozen for reproducibility).

            additional_tests:
                Dictionary mapping test split names
                (e.g. "recent", "temporal_2023")
                to their DataFrames.

    Raises:
        ValueError:
            - If 'split_strategy' is not defined in the configuration.
            - If the configured split strategy is not supported.
    """

    config = load_split_schema(version)

    if "split_strategy" not in config:
        raise ValueError(
            "split_strategy must be defined in split config."
        )

    strategy = config["split_strategy"]

    if strategy == "geographic":
        return geographic_split(df, config, version)

    raise ValueError(f"Unknown split strategy '{strategy}' in split config version {version}.")

