from pathlib import Path
import yaml

from features.feature_schema import (
    get_feature_versions_for_contract,
    get_next_feature_version,
    validate_feature_schema_definition,
    load_feature_schema,
)

from models.model_schema import (
    get_allowed_model_versions,
    get_next_model_version,
    validate_model_schema,
    load_model_schema,
    get_supported_model_definitions as get_supported_model_definitions_core,
)

from utils.active_config import (
    get_active_data_contract_version,
    get_default_feature_version,
    set_default_feature_version,
    get_default_model_version,
    set_default_model_version,
)

FEATURE_DIR = Path("/app/configs/features")
MODEL_DIR = Path("/app/configs/models")


# Feature Schema Service
class FeatureSchemaConfigService:

    # List versions for active data contract
    def list_versions(self):
        contract_version = get_active_data_contract_version()
        versions = get_feature_versions_for_contract(contract_version)

        return {
            "data_contract": contract_version,
            "available_feature_versions": versions,
            "default_feature_version": get_default_feature_version(),
        }

    # Get specific feature schema
    def get_schema(self, version: int):
        schema = load_feature_schema(version)

        if not schema:
            raise ValueError("Feature schema not found")

        return schema

    # Create new feature schema
    def create_schema(self, payload: dict):
        contract_version = get_active_data_contract_version()
        new_version = get_next_feature_version()

        full_schema = {
            "version": new_version,
            "data_contract": contract_version,
            "tabular_features": payload.get("tabular_features", {}),
            "image_features": payload.get("image_features", {}),
        }

        validate_feature_schema_definition(full_schema)

        FEATURE_DIR.mkdir(parents=True, exist_ok=True)
        file_path = FEATURE_DIR / f"v{new_version}.yaml"

        with open(file_path, "w") as f:
            yaml.safe_dump(full_schema, f)

        return {
            "message": "Feature schema created",
            "feature_schema_version": new_version,
        }

    # Set default feature schema
    def set_default(self, version: int):
        contract_version = get_active_data_contract_version()
        available = get_feature_versions_for_contract(contract_version)

        if version not in available:
            raise ValueError("Feature schema not compatible with active data contract")

        set_default_feature_version(version)

        return {
            "message": "Default feature schema updated",
            "feature_schema_version": version,
        }


# Model Schema Service
class ModelSchemaConfigService:

    # List model schema versions
    def list_versions(self):
        versions = get_allowed_model_versions()

        return {
            "available_model_versions": versions,
            "default_model_version": get_default_model_version(),
        }

    # Get specific model schema
    def get_schema(self, version: int):
        schema = load_model_schema(version)

        if not schema:
            raise ValueError("Model schema not found")

        return schema

    # Create new model schema
    def create_schema(self, payload: dict):
        new_version = get_next_model_version()

        full_schema = {
            "version": new_version,
            "model": {
                "type": payload.get("type"),
                "params": payload.get("params", {}),
            },
        }

        validate_model_schema(full_schema)

        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        file_path = MODEL_DIR / f"v{new_version}.yaml"

        with open(file_path, "w") as f:
            yaml.safe_dump(full_schema, f)

        return {
            "message": "Model schema created",
            "model_schema_version": new_version,
        }


    # Set default model schema
    def set_default(self, version: int):
        available = get_allowed_model_versions()

        if version not in available:
            raise ValueError("Model schema not found")

        set_default_model_version(version)

        return {
            "message": "Default model schema updated",
            "model_schema_version": version,
        }

    def get_supported_model_definitions(self):
        return get_supported_model_definitions_core()



feature_schema_config_service = FeatureSchemaConfigService()
model_schema_config_service = ModelSchemaConfigService()
