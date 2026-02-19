import os
import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from pathlib import Path

from typing import Dict, Optional

router = APIRouter(prefix="/configs", tags=["configs"])

CONFIG_ROOT = Path("/opt/project/configs/features")
DATA_CONTRACT_ROOT = Path("/opt/project/configs/data_contracts")


# -------------------------
# Models
# -------------------------

class FeatureOptions(BaseModel):
    type: str  # numeric | categorical
    impute: Optional[str] = None
    clip: Optional[Dict[str, float]] = None
    scaler: Optional[str] = None
    encoding: Optional[str] = None
    order: Optional[list[str]] = None


class FeatureSchemaRequest(BaseModel):
    data_contract_version: int
    target: str
    features: Dict[str, FeatureOptions]


# -------------------------
# Helpers
# -------------------------

def load_data_contract(version: int):
    path = DATA_CONTRACT_ROOT / f"v{version}.yaml"
    if not path.exists():
        raise HTTPException(404, "Data contract not found")
    return yaml.safe_load(path.read_text())


def get_next_version():
    CONFIG_ROOT.mkdir(parents=True, exist_ok=True)
    versions = [
        int(p.stem.replace("v", ""))
        for p in CONFIG_ROOT.glob("v*.yaml")
    ]
    return max(versions, default=0) + 1


# -------------------------
# Validation
# -------------------------

def validate_feature_schema(payload: FeatureSchemaRequest):

    contract = load_data_contract(payload.data_contract_version)
    contract_columns = contract["features"]

    if payload.target not in contract_columns:
        raise HTTPException(400, "Target not in data contract")

    for name, config in payload.features.items():

        if name not in contract_columns:
            raise HTTPException(400, f"{name} not in data contract")

        contract_type = contract_columns[name]["type"]

        # Type validation
        if contract_type in ["float", "int"] and config.type != "numeric":
            raise HTTPException(400, f"{name} must be numeric")

        if contract_type == "string" and config.type != "categorical":
            raise HTTPException(400, f"{name} must be categorical")

        # Numeric-only options
        if config.type == "numeric":
            if config.encoding:
                raise HTTPException(400, f"{name} cannot have encoding")
        # Categorical-only options
        if config.type == "categorical":
            if config.clip or config.scaler:
                raise HTTPException(400, f"{name} cannot have clip/scaler")


# -------------------------
# Endpoint
# -------------------------

@router.post("/features")
def create_feature_schema(payload: FeatureSchemaRequest):

    validate_feature_schema(payload)

    version = get_next_version()

    output = {
        "version": version,
        "created_at": datetime.utcnow().isoformat(),
        "data_contract_version": payload.data_contract_version,
        "target": payload.target,
        "features": payload.features
    }

    path = CONFIG_ROOT / f"v{version}.yaml"
    path.write_text(yaml.dump(output, sort_keys=False))

    return {
        "message": "Feature schema created",
        "version": version
    }
