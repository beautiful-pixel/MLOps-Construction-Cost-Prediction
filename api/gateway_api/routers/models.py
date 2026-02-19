# Models routes

from fastapi import APIRouter, HTTPException
from services.mlflow_client import mlflow_service

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/current")
def current_model():
    try:
        return mlflow_service.get_current_production_model()
    except Exception:
        raise HTTPException(status_code=404, detail="No production model found")


@router.post("/promote")
def promote_model(run_id: str):
    return mlflow_service.promote_to_production(run_id)
