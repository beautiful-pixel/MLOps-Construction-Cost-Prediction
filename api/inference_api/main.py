import os
import time
import logging
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import Response
from prometheus_client import generate_latest, Counter, Histogram, Gauge

from models.loader import load_production_model
from registry.model_registry import get_model_version_from_alias
from registry.run_metadata import get_run_config
from utils.logger import setup_logging
from inference.schema_builder import build_pydantic_model
from utils.mlflow_config import get_model_name
from features.feature_schema import get_ordered_features



# Logging

setup_logging("inference_api")

# Environment configuration

API_TITLE = os.getenv("INFERENCE_API_TITLE", "Inference API")
INFERENCE_INTERNAL_TOKEN = os.getenv("INFERENCE_INTERNAL_TOKEN")

# FastAPI app

app = FastAPI(
    title=API_TITLE,
    version="1.0",
)

# Prometheus metrics

request_count = Counter(
    "api_requests_total",
    "Total API requests"
)

request_latency = Histogram(
    "api_request_duration_seconds",
    "API request latency in seconds"
)

model_version_gauge = Gauge(
    "served_model_version",
    "Model version served"
)


# Global state (loaded at startup)

model: Optional[object] = None
served_model_version: Optional[str] = None
feature_version: Optional[int] = None
FEATURE_ORDER: Optional[list[str]] = None
InputModel = None


def require_internal_token(authorization: str | None = Header(default=None)):
    if not INFERENCE_INTERNAL_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="INFERENCE_INTERNAL_TOKEN not configured",
        )

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=403, detail="Forbidden")

    token = authorization.split(" ", 1)[1]
    if token != INFERENCE_INTERNAL_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")


# Startup event

@app.on_event("startup")
def startup_event():
    global model
    global served_model_version
    global feature_version
    global FEATURE_ORDER
    global InputModel

    logging.info("Starting inference API initialization")

    try:
        model_name = get_model_name()

        model = load_production_model(model_name=model_name)

        mv = get_model_version_from_alias(model_name, "prod")
        if mv is not None:
            served_model_version = str(mv.version)

        run_id = getattr(model.metadata, "run_id", None)
        if run_id is None:
            raise RuntimeError("Unable to retrieve run_id from model metadata")

        config = get_run_config(run_id)

        feature_version = config["feature_version"]

        FEATURE_ORDER = get_ordered_features(feature_version)

        InputModel = build_pydantic_model(feature_version)

        if served_model_version is not None:
            try:
                model_version_gauge.set(float(served_model_version))
            except ValueError:
                logging.warning("Model version is not numeric, gauge not set.")

        logging.info(
            "Model loaded successfully | "
            f"run_id={run_id} | "
            f"feature_version={feature_version}"
        )

    except Exception:
        logging.warning("No production model available.")
        model = None


# Prediction endpoint

@app.post("/predict")
def predict(payload: dict, internal=Depends(require_internal_token)):

    if model is None:
        raise HTTPException(
            status_code=503,
            detail="No production model loaded"
        )

    start_time = time.time()

    try:
        # Validate using dynamic Pydantic model
        validated = InputModel(**payload)
        input_dict = validated.model_dump()

        # Use DataFrame to preserve feature alignment
        input_df = pd.DataFrame([input_dict])

        prediction = model.predict(input_df)
        prediction_value = float(prediction[0])

        request_count.inc()
        request_latency.observe(time.time() - start_time)

        return {
            "prediction": prediction_value,
            "model_version": served_model_version,
            "feature_version": feature_version,
        }

    except Exception:
        logging.exception("Prediction error")
        raise HTTPException(
            status_code=500,
            detail="Prediction failed"
        )


# Health endpoint

@app.get("/health")
def health(internal=Depends(require_internal_token)):

    if model is None:
        return {
            "status": "no_model_loaded"
        }

    return {
        "status": "ok",
        "model_version": served_model_version,
        "feature_version": feature_version,
    }


# Prometheus metrics endpoint

@app.get("/metrics")
def metrics():
    return Response(
        generate_latest(),
        media_type="text/plain"
    )

# Schema endpoint
@app.get("/schema")
def get_schema(internal=Depends(require_internal_token)):
    if InputModel is None:
        raise HTTPException(status_code=503, detail="Model not initialized")

    return InputModel.model_json_schema()
