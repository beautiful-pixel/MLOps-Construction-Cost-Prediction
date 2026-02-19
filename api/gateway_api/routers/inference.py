from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from services.inference_client import predict, get_schema

router = APIRouter(tags=["inference"])


@router.post("/predict")
def proxy_predict(payload: Dict[str, Any]):
    try:
        return predict(payload)
    except Exception:
        raise HTTPException(503, "Inference service unavailable")


@router.get("/schema")
def proxy_schema():
    try:
        return get_schema()
    except Exception:
        raise HTTPException(503, "Inference service unavailable")
