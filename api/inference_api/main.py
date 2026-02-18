import os
import time
import logging
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from prometheus_client import generate_latest, Counter, Histogram, Gauge

from models.loader import load_production_model
from registry.run_metadata import get_run_config
from utils.logger import setup_logging
from inference.schema_builder import build_pydantic_model
from utils.mlflow_config import get_model_name
from features.feature_schema import get_ordered_features



# Logging

setup_logging("inference_api")

# Environment configuration

API_TITLE = os.getenv("INFERENCE_API_TITLE", "Inference API")
MODEL_VERSION = 1

# FastAPI app

app = FastAPI(
    title=API_TITLE,
    version=str(MODEL_VERSION),
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

# Set gauge only if numeric
try:
    model_version_gauge.set(float(MODEL_VERSION))
except ValueError:
    logging.warning("MODEL_VERSION is not numeric, gauge not set.")


# Global state (loaded at startup)

model: Optional[object] = None
feature_version: Optional[int] = None
FEATURE_ORDER: Optional[list[str]] = None
InputModel = None


# Startup event

@app.on_event("startup")
def startup_event():
    global model
    global feature_version
    global FEATURE_ORDER
    global InputModel

    logging.info("Starting inference API initialization")

    try:
        model_name = get_model_name()

        model = load_production_model(model_name=model_name)

        run_id = getattr(model.metadata, "run_id", None)
        if run_id is None:
            raise RuntimeError("Unable to retrieve run_id from model metadata")

        config = get_run_config(run_id)

        feature_version = config["feature_version"]

        FEATURE_ORDER = get_ordered_features(feature_version)

        InputModel = build_pydantic_model(feature_version)

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
def predict(payload: dict):

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
            "model_version": MODEL_VERSION,
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
def health():

    if model is None:
        return {
            "status": "no_model_loaded"
        }

    return {
        "status": "ok",
        "model_version": MODEL_VERSION,
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
def get_schema():
    if InputModel is None:
        raise HTTPException(status_code=503, detail="Model not initialized")

    return InputModel.model_json_schema()

