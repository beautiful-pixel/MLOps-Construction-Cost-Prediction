import os
import requests
from fastapi import FastAPI, HTTPException
from mlflow.tracking import MlflowClient
from pydantic import BaseModel
from typing import Dict, Any

# Environment

AIRFLOW_URL = os.getenv("AIRFLOW_URL", "http://airflow-webserver:8080")
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
INFERENCE_API_URL = os.getenv("INFERENCE_API_URL", "http://inference-api:8000")

# MLflow client
client = MlflowClient(tracking_uri=MLFLOW_TRACKING_URI)

app = FastAPI(title="MLOps Gateway API", version="1.0")


# -------------------------
# Models
# -------------------------

class TrainingRequest(BaseModel):
    feature_version: int
    split_version: int
    model_config_version: int


# -------------------------
# Health
# -------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


# -------------------------
# Current model info
# -------------------------

@app.get("/models/current")
def get_current_model():

    try:
        mv = client.get_model_version_by_alias(
            name="construction_cost_model",
            alias="prod"
        )

        run = client.get_run(mv.run_id)

        return {
            "registered_model_version": mv.version,
            "run_id": mv.run_id,
            "feature_version": run.data.params.get("feature_version"),
            "split_version": run.data.params.get("split_version"),
        }

    except Exception:
        raise HTTPException(
            status_code=404,
            detail="No production model found"
        )


# -------------------------
# Proxy Predict
# -------------------------

@app.post("/predict")
def proxy_predict(payload: Dict[str, Any]):

    try:
        response = requests.post(
            f"{INFERENCE_API_URL}/predict",
            json=payload,
            timeout=5
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text
            )

        return response.json()

    except requests.exceptions.RequestException:
        raise HTTPException(
            status_code=503,
            detail="Inference service unavailable"
        )


# -------------------------
# Proxy Schema
# -------------------------

@app.get("/schema")
def proxy_schema():

    try:
        response = requests.get(
            f"{INFERENCE_API_URL}/schema",
            timeout=5
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text
            )

        return response.json()

    except requests.exceptions.RequestException:
        raise HTTPException(
            status_code=503,
            detail="Inference service unavailable"
        )


# -------------------------
# Trigger training
# -------------------------

@app.post("/training/run")
def trigger_training(request: TrainingRequest):

    dag_id = "train_pipeline_dag"

    try:
        response = requests.post(
            f"{AIRFLOW_URL}/api/v1/dags/{dag_id}/dagRuns",
            json={
                "conf": {
                    "feature_version": request.feature_version,
                    "split_version": request.split_version,
                    "model_version": request.model_config_version
                }
            },
            auth=("admin", "admin"),
            timeout=5
        )

        if response.status_code not in [200, 201]:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text
            )

        return response.json()

    except requests.exceptions.RequestException:
        raise HTTPException(
            status_code=503,
            detail="Airflow unreachable"
        )
