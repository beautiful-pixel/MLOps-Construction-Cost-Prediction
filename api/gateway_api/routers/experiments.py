# Experiments routes

from fastapi import APIRouter, Depends
from services.mlflow_client import mlflow_service
from services.security import require_admin

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.get("/")
def list_experiments(user=Depends(require_admin)):
    return mlflow_service.list_experiments()


@router.get("/{experiment_id}/runs")
def list_runs(experiment_id: str, user=Depends(require_admin)):
    return mlflow_service.list_runs(experiment_id)
