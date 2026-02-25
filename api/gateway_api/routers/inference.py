from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

from services.inference_client import predict, get_schema, reload_model
from services.security import require_user, require_admin

router = APIRouter(tags=["inference"])


@router.post("/predict")
def proxy_predict(payload: Dict[str, Any], user=Depends(require_user)):
    try:
        return predict(payload)
    except Exception:
        raise HTTPException(503, "Inference service unavailable")


@router.get("/schema")
def proxy_schema(user=Depends(require_user)):
    try:
        return get_schema()
    except Exception:
        raise HTTPException(503, "Inference service unavailable")


@router.post("/reload")
def reload_inference_model(user=Depends(require_admin)):
    """Admin-only: ask inference service to reload the production model."""
    try:
        return reload_model()
    except Exception:
        raise HTTPException(503, "Inference service reload unavailable")
