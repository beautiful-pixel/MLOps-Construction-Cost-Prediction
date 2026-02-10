from fastapi import FastAPI
import requests

# exemple à adapter pour faire du proxy vers les autres services (inference, airflow) en attendant d'avoir une vraie UI

app = FastAPI(title="Solafune Gateway API")

INFERENCE_URL = "http://inference-api:8000/predict"
AIRFLOW_URL = "http://airflow:8080/api/v1/dags/train_dag/dagRuns"

@app.post("/predict")
def predict(payload: dict):
    return requests.post(INFERENCE_URL, json=payload).json()

@app.post("/train")
def train():
    return requests.post(AIRFLOW_URL, json={"conf": {}}).json()