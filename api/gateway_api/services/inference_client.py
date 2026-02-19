import os
import requests

INFERENCE_API_URL = os.getenv(
    "INFERENCE_API_URL",
    "http://inference-api:8000"
)

# Inference healthcheck
class InferenceClient:

    def __init__(self):
        self.base_url = INFERENCE_API_URL

    def healthcheck(self) -> bool:
        response = requests.get(f"{self.base_url}/health")
        return response.status_code == 200


def predict(payload: dict):

    response = requests.post(
        f"{INFERENCE_API_URL}/predict",
        json=payload,
        timeout=5
    )

    response.raise_for_status()
    return response.json()


def get_schema():

    response = requests.get(
        f"{INFERENCE_API_URL}/schema",
        timeout=5
    )

    response.raise_for_status()
    return response.json()
