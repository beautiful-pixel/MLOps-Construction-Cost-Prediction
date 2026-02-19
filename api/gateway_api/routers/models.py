# Models routes

from fastapi import APIRouter, HTTPException, Depends
from services.mlflow_client import mlflow_service
from services.security import require_admin, require_user

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/current")
def current_model(user=Depends(require_user)):
    try:
        return mlflow_service.get_current_production_model()
    except Exception:
        raise HTTPException(status_code=404, detail="No production model found")


@router.post("/promote")
def promote_model(run_id: str, user=Depends(require_admin)):
    return mlflow_service.promote_to_production(run_id)
