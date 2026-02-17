# main.py

import os
import time
import logging
import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from prometheus_client import generate_latest, Counter, Histogram, Gauge
from mlflow import pyfunc

from model_loader import load_model_and_metadata
from schema_builder import build_pydantic_model

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("solafune-api")

MODEL_VERSION = os.getenv("MODEL_VERSION")

if not MODEL_VERSION:
    raise RuntimeError("MODEL_VERSION environment variable is required.")

# Load model + feature schema from MLflow
model, feature_schema, feature_version = load_model_and_metadata(MODEL_VERSION)

# Build dynamic Pydantic model
InputModel = build_pydantic_model(feature_schema)

app = FastAPI(
    title="Solafune Inference API",
    version=MODEL_VERSION,
)

# Prometheus metrics
request_count = Counter("api_requests_total", "Total API requests")
request_latency = Histogram("api_request_duration_seconds", "Request latency")
model_version_gauge = Gauge("served_model_version", "Model version served")
model_version_gauge.set(int(MODEL_VERSION))

@app.post("/predict")
def predict(payload: InputModel):
    start_time = time.time()

    try:
        input_dict = payload.model_dump()
        input_array = np.array([list(input_dict.values())])

        prediction = model.predict(input_array)
        prediction_value = float(prediction[0])

        request_count.inc()
        request_latency.observe(time.time() - start_time)

        return {
            "prediction": prediction_value,
            "model_version": MODEL_VERSION,
            "feature_version": feature_version,
        }

    except Exception as e:
        logger.error("Prediction error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_version": MODEL_VERSION,
        "feature_version": feature_version,
    }


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")
