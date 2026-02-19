from fastapi import APIRouter, HTTPException
from services.config_service import model_schema_config_service

router = APIRouter(
    prefix="/configs/model-schemas",
    tags=["model-schemas"]
)




# List versions

@router.get("")
def list_model_versions():
    try:
        return model_schema_config_service.list_versions()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/supported")
def get_supported_models():
    return model_schema_config_service.get_supported_model_definitions()

# Get specific version

@router.get("/{version}")
def get_model_schema(version: int):
    try:
        return model_schema_config_service.get_schema(version)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# Create new model schema

@router.post("")
def create_model_schema(payload: dict):
    try:
        return model_schema_config_service.create_schema(payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Set default version

@router.post("/default")
def set_default_model(version: int):
    try:
        return model_schema_config_service.set_default(version)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
