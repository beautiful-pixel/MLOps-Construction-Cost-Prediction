"""
Model schema management utilities.

This module centralizes everything related to
versioned model configurations:

- Loading model configuration by version
- Validating available versions
- Validating schema structure and integrity
- Building model instance from version only

All functions operate from a schema version integer

This ensures:
- Reproducible model definitions
- Clean separation between model config and training logic
- Version consistency across pipeline stages
"""

from pathlib import Path
from typing import Dict, List, Type
import yaml

from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge


# Paths

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_CONFIG_DIR = PROJECT_ROOT / "configs" / "models"


# Supported models registry

SUPPORTED_MODELS: Dict[str, Type] = {
    "gradient_boosting": GradientBoostingRegressor,
    "random_forest": RandomForestRegressor,
    "ridge": Ridge,
}


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

def get_next_model_version() -> int:
    """
    Return next model schema version number (incremental).
    """

    versions = get_allowed_model_versions()

    if not versions:
        return 1

    return max(versions) + 1

def get_supported_model_definitions() -> Dict:
    """
    Return supported model types with their valid parameters
    and default values.

    Used by API to expose model configuration capabilities
    to frontend (e.g. Streamlit).
    """

    models_info = {}

    for model_name, model_class in SUPPORTED_MODELS.items():

        instance = model_class()
        params = instance.get_params()

        param_definitions = {}

        for param_name, default_value in params.items():

            param_definitions[param_name] = {
                "default": default_value,
                "type": type(default_value).__name__,
            }

        models_info[model_name] = {
            "parameters": param_definitions
        }

    return models_info



# Loading

def load_model_schema(version: int) -> Dict:
    """
    Load model configuration for a given version.
    """

    allowed_versions = get_allowed_model_versions()

    if version not in allowed_versions:
        raise ValueError(
            f"Model version {version} not available. "
            f"Allowed versions: {allowed_versions}"
        )

    config_path = MODEL_CONFIG_DIR / f"v{version}.yaml"

    with open(config_path, "r") as f:
        return yaml.safe_load(f)


# Validation

def validate_model_schema(schema: Dict) -> None:
    """
    Validate structure and integrity of a model schema definition.

    Used when creating a new model version via API
    or when loading a model configuration.
    """

    # Required top-level keys
    required_keys = {"version", "model"}

    missing_keys = required_keys - set(schema.keys())
    if missing_keys:
        raise ValueError(
            f"Missing required top-level keys: {missing_keys}"
        )

    if not isinstance(schema["version"], int):
        raise ValueError("'version' must be an integer.")

    model_section = schema["model"]

    if not isinstance(model_section, dict):
        raise ValueError("'model' must be a dictionary.")

    # Required model keys
    required_model_keys = {"type", "params"}

    missing_model_keys = required_model_keys - set(model_section.keys())
    if missing_model_keys:
        raise ValueError(
            f"Missing required keys in 'model': {missing_model_keys}"
        )

    model_type = model_section["type"]
    params = model_section["params"]

    if not isinstance(model_type, str):
        raise ValueError("'model.type' must be a string.")

    if model_type not in SUPPORTED_MODELS:
        raise ValueError(
            f"Unsupported model type '{model_type}'. "
            f"Supported types: {list(SUPPORTED_MODELS.keys())}"
        )

    if not isinstance(params, dict):
        raise ValueError("'model.params' must be a dictionary.")

    # Validate parameters dynamically using sklearn introspection
    model_class = SUPPORTED_MODELS[model_type]
    valid_params = model_class().get_params().keys()

    invalid_params = set(params.keys()) - set(valid_params)

    if invalid_params:
        raise ValueError(
            f"Invalid parameters for '{model_type}': {invalid_params}. "
            f"Valid parameters are: {sorted(valid_params)}"
        )

    # Optional: ensure no unexpected keys exist in model section
    extra_model_keys = set(model_section.keys()) - required_model_keys
    if extra_model_keys:
        raise ValueError(
            f"Unexpected keys in 'model' section: {extra_model_keys}"
        )


# Builder

def build_model(version: int):
    """
    Instantiate model from versioned schema.
    """

    schema = load_model_schema(version)
    validate_model_schema(schema)

    model_type = schema["model"]["type"]
    params = schema["model"]["params"]

    model_class = SUPPORTED_MODELS[model_type]

    try:
        return model_class(**params)
    except TypeError as e:
        raise ValueError(
            f"Failed to instantiate model '{model_type}' "
            f"with params {params}: {e}"
        )
