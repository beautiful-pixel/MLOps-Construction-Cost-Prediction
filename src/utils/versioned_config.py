"""
Generic utilities for versioned YAML configurations.

This module provides reusable helpers to:
- List available versions
- Load versioned YAML files

Used by:
- data_schema
- feature_schema
- split_schema
- model_schema
"""

from pathlib import Path
from typing import Dict, List
import yaml
import os


# Paths

# Require explicit CONFIG_ROOT env var. No fallback to project-relative paths.
CONFIG_ROOT = os.getenv("CONFIG_ROOT")
if not CONFIG_ROOT:
    raise RuntimeError("CONFIG_ROOT environment variable is not defined")

CONFIG_ROOT = Path(CONFIG_ROOT).resolve()


def _get_config_dir(folder_name: str) -> Path:
    """
    Return configuration directory for a given folder name.

    """
    config_dir = CONFIG_ROOT / folder_name

    if not config_dir.exists():
        raise ValueError(
            f"Configuration directory '{folder_name}' does not exist "
            f"under {CONFIG_ROOT}."
        )

    return config_dir


def get_available_versions(folder_name: str) -> List[int]:
    """
    Return available version numbers for a config folder name.

    Args:
        folder_name (str): Config folder name.

    Returns:
        List[int]: Sorted list of available versions.
    """
    config_dir = _get_config_dir(folder_name)

    versions = []

    for path in config_dir.glob("v*.yaml"):
        if path.is_file() and path.stem.startswith("v"):
            try:
                versions.append(int(path.stem[1:]))
            except ValueError:
                continue

    return sorted(versions)


def load_versioned_yaml(folder_name: str, version: int) -> Dict:
    """
    Load a versioned YAML configuration.

    Args:
        folder_name (str): Config folder name.
        version (int): Version number (e.g. 1 loads v1.yaml).

    Returns:
        Dict: Parsed YAML configuration.

    Raises:
        ValueError: If version does not exist.
    """
    config_dir = _get_config_dir(folder_name)
    available = get_available_versions(folder_name)

    if version not in available:
        raise ValueError(
            f"Unknown version '{version}' for '{folder_name}'. "
            f"Available versions: {available}"
        )

    path = config_dir / f"v{version}.yaml"

    with open(path, "r") as f:
        config = yaml.safe_load(f)

    if not config:
        raise ValueError(
            f"Configuration file {path} is empty or invalid."
        )

    return config

