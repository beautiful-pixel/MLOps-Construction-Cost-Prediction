"""
Active configuration management utilities.

This module centralizes access to the active pipeline configuration.

The active configuration defines:

- The structural data contract version (system-level constraint)
- The default training strategy versions (feature, split, model)

IMPORTANT:
-------------
This module does NOT apply any business logic.
It only loads and exposes configuration values.

Version resolution and overrides must happen at orchestration level
(e.g. in DAGs or CLI entrypoints), not inside core logic modules.
"""
import os
from pathlib import Path
from typing import Dict
import yaml

from features.feature_schema import get_feature_versions_for_contract
from models.model_schema import get_allowed_model_versions
from splitting.split_schema import get_split_versions_for_contract


# Paths
CONFIG_ROOT = os.getenv("CONFIG_ROOT")

if not CONFIG_ROOT:
    raise RuntimeError(
        "CONFIG_ROOT environment variable is not defined."
    )

CONFIG_ROOT = Path(CONFIG_ROOT).resolve()
ACTIVE_CONFIG_PATH = CONFIG_ROOT / "active_config.yaml"

if not ACTIVE_CONFIG_PATH.exists():
    raise FileNotFoundError(
        f"Active config file not found at {ACTIVE_CONFIG_PATH}"
    )

# PROJECT_ROOT = Path(__file__).resolve().parents[2]
# ACTIVE_CONFIG_PATH = PROJECT_ROOT / "configs" / "active_config.yaml"


# Core loader

def load_active_config() -> Dict:
    """
    Load the active configuration file.

    Returns:
        Dict: Parsed YAML configuration.

    Raises:
        FileNotFoundError: If active_config.yaml is missing.
        ValueError: If the file is empty or invalid.
    """
    if not ACTIVE_CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Active config file not found at {ACTIVE_CONFIG_PATH}"
        )

    with open(ACTIVE_CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)

    if not config:
        raise ValueError("Active config file is empty or invalid.")

    return config


# Structural Layer

def get_active_data_contract_version() -> int:
    """
    Return the structural data contract version.

    This defines the expected dataset schema and validation rules.

    Returns:
        int: Data contract version.

    Raises:
        KeyError: If key is missing.
    """
    config = load_active_config()
    return config["data_contract_version"]


# Training Default Layer

def get_default_feature_version() -> int:
    """
    Return the default feature configuration version
    used for training when no override is provided.

    Returns:
        int: Feature configuration version.

    Raises:
        KeyError: If key is missing.
    """
    config = load_active_config()
    return config["training_defaults"]["feature_version"]


def get_default_split_version() -> int:
    """
    Return the default split configuration version
    used for training when no override is provided.

    Returns:
        int: Split configuration version.

    Raises:
        KeyError: If key is missing.
    """
    config = load_active_config()
    return config["training_defaults"]["split_version"]


def get_default_model_version() -> int:
    """
    Return the default model configuration version
    used for training when no override is provided.

    Returns:
        int: Model configuration version.

    Raises:
        KeyError: If key is missing.
    """
    config = load_active_config()
    return config["training_defaults"]["model_version"]


def get_available_feature_versions_for_active_contract() -> list[int]:
    """
    Return feature versions attached to the active data contract.
    """
    contract_version = get_active_data_contract_version()
    return get_feature_versions_for_contract(contract_version)


def _update_training_default(key: str, version: int) -> None:
    """
    Generic helper to update a training default version.
    """

    config = load_active_config()

    if "training_defaults" not in config:
        config["training_defaults"] = {}

    config["training_defaults"][key] = version

    with open(ACTIVE_CONFIG_PATH, "w") as f:
        yaml.dump(config, f)

def set_default_feature_version(version: int) -> None:
    """
    Update default feature version.

    Ensures compatibility with active data contract.
    """

    contract_version = get_active_data_contract_version()
    available = get_feature_versions_for_contract(contract_version)

    if version not in available:
        raise ValueError(
            f"Feature version {version} "
            f"is not compatible with active data contract."
        )

    _update_training_default("feature_version", version)

def set_default_split_version(version: int) -> None:
    """
    Update default split version.

    Ensures compatibility with active data contract.
    """

    contract_version = get_active_data_contract_version()
    available = get_split_versions_for_contract(contract_version)

    if version not in available:
        raise ValueError(
            f"Split version {version} "
            f"is not compatible with active data contract."
        )

    _update_training_default("split_version", version)


def set_default_model_version(version: int) -> None:
    """
    Update default model version.
    """

    available = get_allowed_model_versions()

    if version not in available:
        raise ValueError(
            f"Model version {version} does not exist."
        )

    _update_training_default("model_version", version)


