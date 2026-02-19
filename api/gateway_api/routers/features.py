from fastapi import APIRouter, HTTPException, Depends
from services.config_service import feature_schema_config_service
from services.security import require_admin

router = APIRouter(
    prefix="/configs/feature-schemas",
    tags=["feature-schemas"]
)



# List versions

@router.get("")
def list_feature_versions(user=Depends(require_admin)):
    try:
        return feature_schema_config_service.list_versions()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# Get specific version

@router.get("/{version}")
def get_feature_schema(version: int, user=Depends(require_admin)):
    try:
        return feature_schema_config_service.get_schema(version)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))



# Create new feature schema

@router.post("")
def create_feature_schema(payload: dict, user=Depends(require_admin)):
    try:
        return feature_schema_config_service.create_schema(payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



# Set default version

@router.post("/default")
def set_default_feature(version: int, user=Depends(require_admin)):
    try:
        return feature_schema_config_service.set_default(version)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
