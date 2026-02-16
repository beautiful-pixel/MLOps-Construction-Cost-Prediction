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

from pathlib import Path
from typing import Dict
import yaml


# Paths

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ACTIVE_CONFIG_PATH = PROJECT_ROOT / "configs" / "active_config.yaml"


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
