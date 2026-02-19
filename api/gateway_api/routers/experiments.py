# Experiments routes

from fastapi import APIRouter
from services.mlflow_client import mlflow_service

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.get("/")
def list_experiments():
    return mlflow_service.list_experiments()


@router.get("/{experiment_id}/runs")
def list_runs(experiment_id: str):
    return mlflow_service.list_runs(experiment_id)
