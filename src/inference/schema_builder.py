from pydantic import BaseModel, Field, create_model
from typing import Literal
import re
from features.feature_schema import load_feature_schema
from data.data_contract import load_data_contract

TYPE_MAPPING = {
    "int": int,
    "float": float,
    "string": str,
}


def build_pydantic_model(feature_version: int) -> type[BaseModel]:

    feature_schema = load_feature_schema(feature_version)
    data_contract_version = feature_schema["data_contract"]
    data_schema = load_data_contract(data_contract_version)

    tabular_features = feature_schema["tabular_features"]
    contract_columns = data_schema["columns"]

    fields = {}

    for feature_name, feature_config in tabular_features.items():

        contract_config = contract_columns[feature_name]

        # Python type
        base_type = TYPE_MAPPING[contract_config["type"]]

        # Allowed values
        if "allowed_values" in contract_config:
            base_type = Literal[tuple(contract_config["allowed_values"])]

        field_args = {}

        # Numeric constraints
        if contract_config["type"] in ["int", "float"]:
            if "min" in contract_config:
                field_args["ge"] = contract_config["min"]
            if "max" in contract_config:
                field_args["le"] = contract_config["max"]

        # Regex constraint
        if "format" in contract_config:
            field_args["pattern"] = contract_config["format"]

        # Required logic
        is_required = "impute" not in feature_config

        default = ... if is_required else None

        fields[feature_name] = (
            base_type,
            Field(default, **field_args)
        )

    return create_model("DynamicInputModel", **fields)
