"""
Model schema management utilities.

Centralized handling of versioned model configurations.
"""

from typing import Dict, List, Type
import yaml

from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge

from utils.versioned_config import (
    load_versioned_yaml,
    get_available_versions,
)


# Supported models registry

SUPPORTED_MODELS: Dict[str, Type] = {
    "gradient_boosting": GradientBoostingRegressor,
    "random_forest": RandomForestRegressor,
    "ridge": Ridge,
}


# Version utilities

def get_allowed_model_versions() -> List[int]:
    """
    Return available model schema versions.
    """
    return get_available_versions("models")


def get_next_model_version() -> int:
    """
    Return next model schema version number.
    """
    versions = get_allowed_model_versions()

    if not versions:
        return 1

    return max(versions) + 1


def get_supported_model_definitions() -> Dict:
    """
    Return supported model types with their parameters
    and default values.
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

    return load_versioned_yaml("models", version)


# Validation

def validate_model_schema(schema: Dict) -> None:
    """
    Validate structure and integrity of a model schema definition.
    """

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

    model_class = SUPPORTED_MODELS[model_type]
    valid_params = model_class().get_params().keys()

    invalid_params = set(params.keys()) - set(valid_params)

    if invalid_params:
        raise ValueError(
            f"Invalid parameters for '{model_type}': {invalid_params}. "
            f"Valid parameters are: {sorted(valid_params)}"
        )

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