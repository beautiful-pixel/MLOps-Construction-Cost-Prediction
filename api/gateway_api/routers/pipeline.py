# Pipeline routes

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Optional

from services.airflow_client import airflow_service
from services.security import require_admin

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


# Request model for trigger
class TriggerRequest(BaseModel):
    dag_id: str
    conf: Optional[Dict] = None


# List dags
@router.get("/dags")
def list_dags(user=Depends(require_admin)):
    try:
        return airflow_service.list_dags()
    except Exception as e:
        raise HTTPException(500, str(e))


# Trigger dag
@router.post("/trigger")
def trigger_pipeline(request: TriggerRequest, user=Depends(require_admin)):
    try:
        return airflow_service.trigger_dag(
            dag_id=request.dag_id,
            conf=request.conf,
        )
    except Exception as e:
        raise HTTPException(500, str(e))


# List dag runs
@router.get("/dags/{dag_id}/runs")
def list_runs(dag_id: str, user=Depends(require_admin)):
    try:
        return airflow_service.list_dag_runs(dag_id)
    except Exception as e:
        raise HTTPException(500, str(e))


# List task instances
@router.get("/dags/{dag_id}/runs/{dag_run_id}/tasks")
def list_tasks(dag_id: str, dag_run_id: str, user=Depends(require_admin)):
    try:
        return airflow_service.list_task_instances(dag_id, dag_run_id)
    except Exception as e:
        raise HTTPException(500, str(e))
