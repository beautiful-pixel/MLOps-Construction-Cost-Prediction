from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from services.airflow_client import airflow_service
from services.security import require_admin

router = APIRouter(prefix="/training", tags=["training"])


class TrainingRequest(BaseModel):
    feature_version: int
    split_version: int
    model_config_version: int


@router.post("/run")
def run_training(request: TrainingRequest, user=Depends(require_admin)):

    dag_id = "train_pipeline_dag"

    try:
        result = airflow_service.trigger_dag(
            dag_id,
            conf={
                "feature_version": request.feature_version,
                "split_version": request.split_version,
                "model_version": request.model_config_version,
            }
        )

        return result

    except Exception as e:
        raise HTTPException(500, str(e))

