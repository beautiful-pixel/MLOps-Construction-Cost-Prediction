"""
Model schema management utilities.

This module centralizes everything related to
versioned model configurations:

- Loading model configuration by version
- Validating available versions
- Accessing model type and parameters
- Building model instance from version only

All functions operate from a schema version integer

This ensures:
- Reproducible model definitions
- Clean separation between model config and training logic
- Version consistency across pipeline stages
"""

from pathlib import Path
from typing import Dict, List
import yaml

from utils.versioned_config import load_versioned_yaml, get_available_versions

from sklearn.ensemble import GradientBoostingRegressor


# Paths

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_CONFIG_DIR = PROJECT_ROOT / "configs" / "models"


# Version utilities

def get_allowed_model_versions() -> List[int]:
    """
    Return available model versions.
    """
    versions = []

    for file in MODEL_CONFIG_DIR.glob("v*.yaml"):
        version = int(file.stem.replace("v", ""))
        versions.append(version)

    return sorted(versions)


# Loading

def load_model_schema(version: int) -> Dict:
    """
    Load model configuration for a given version.
    """

    if version not in get_allowed_model_versions():
        raise ValueError(
            f"Model version {version} not available. "
            f"Allowed versions: {get_allowed_model_versions()}"
        )

    config_path = MODEL_CONFIG_DIR / f"v{version}.yaml"

    with open(config_path, "r") as f:
        return yaml.safe_load(f)


# Validation

def validate_model_schema(schema: Dict) -> None:
    """
    Validate model schema structure.
    """

    if "model" not in schema:
        raise ValueError("Missing 'model' section in schema.")

    model_section = schema["model"]

    if "type" not in model_section:
        raise ValueError("Missing 'model.type'.")

    if "params" not in model_section:
        raise ValueError("Missing 'model.params'.")

    if not isinstance(model_section["params"], dict):
        raise ValueError("'model.params' must be a dictionary.")


# Builder

def build_model(version: int):
    """
    Instantiate model from versioned schema.
    """

    schema = load_model_schema(version)
    validate_model_schema(schema)

    model_type = schema["model"]["type"]
    params = schema["model"]["params"]

    if model_type == "gradient_boosting":
        return GradientBoostingRegressor(**params)

    raise ValueError(f"Unsupported model type: {model_type}")
