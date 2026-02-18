import os
import requests
from fastapi import FastAPI, HTTPException
from mlflow.tracking import MlflowClient
from pydantic import BaseModel

# Environment

AIRFLOW_URL = os.getenv("AIRFLOW_URL", "http://airflow-webserver:8080")
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")

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

        return {
            "status_code": response.status_code,
            "response_text": response.text
        }

    except Exception as e:
        return {
            "error": str(e)
        }
