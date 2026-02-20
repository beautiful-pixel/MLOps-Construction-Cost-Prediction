from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from services.system_service import SystemService
from services.security import require_admin, require_user
from services.mlflow_client import mlflow_service
from registry.run_metadata import get_run_metrics, get_run_config
from utils.data_versioning import get_data_lineage

router = APIRouter(
    prefix="",
    tags=["system"]
)

@router.get("/health")
def health():
    return {"status": "ok"}

system_service = SystemService()

@router.get("/status")
def get_system_status(user=Depends(require_admin)):
    return system_service.get_status()


@router.get("/info")
def get_system_info(user=Depends(require_user)):
    try:
        model_info = mlflow_service.get_current_production_model()
    except Exception:
        raise HTTPException(
            status_code=404,
            detail="No production model found",
        )

    run_id = model_info.get("run_id")
    if not run_id:
        raise HTTPException(
            status_code=500,
            detail="Production model run_id not available",
        )

    all_metrics = get_run_metrics(run_id)
    key_metric_names = [
        "reference_rmsle",
        "reference_mae",
        "reference_r2",
        "train_rmsle",
        "train_mae",
        "train_r2",
    ]
    key_metrics = {
        name: all_metrics[name]
        for name in key_metric_names
        if name in all_metrics
    }

    payload = {
        "model_version": model_info.get("registered_model_version"),
        "run_id": run_id,
        "feature_version": model_info.get("feature_version"),
        "split_version": model_info.get("split_version"),
        "metrics": key_metrics,
    }

    try:
        run = mlflow_service.client.get_run(run_id)
        timestamp_ms = run.info.end_time or run.info.start_time
    except Exception:
        timestamp_ms = None

    if timestamp_ms:
        payload["model_last_updated_at"] = datetime.fromtimestamp(
            timestamp_ms / 1000,
            tz=timezone.utc,
        ).isoformat()
    else:
        payload["model_last_updated_at"] = None

    if user.get("role") == "admin":
        try:
            config = get_run_config(run_id)
            lineage = get_data_lineage(config["split_version"])
        except Exception:
            lineage = None
        payload["data_version"] = lineage

    return payload
