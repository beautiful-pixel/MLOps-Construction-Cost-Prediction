# routers/datasets.py

from fastapi import APIRouter, HTTPException, Depends

from services.dataset_service import compute_dataset_overview
from services.airflow_client import airflow_service
from services.security import require_admin

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("/overview")
def get_overview(user=Depends(require_admin)):
    try:
        return compute_dataset_overview(airflow_service)
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/threshold")
def update_threshold(threshold: int, user=Depends(require_admin)):
    try:
        airflow_service.set_variable(
            "RETRAIN_THRESHOLD_ROWS",
            str(threshold),
        )
        return {"threshold": threshold}
    except Exception as e:
        raise HTTPException(500, str(e))