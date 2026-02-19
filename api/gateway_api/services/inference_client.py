import os
import requests

INFERENCE_API_URL = os.getenv(
    "INFERENCE_API_URL",
    "http://inference-api:8000"
)
INFERENCE_INTERNAL_TOKEN = os.getenv("INFERENCE_INTERNAL_TOKEN")


def _auth_headers() -> dict:
    if not INFERENCE_INTERNAL_TOKEN:
        raise RuntimeError("INFERENCE_INTERNAL_TOKEN not set")
    return {"Authorization": f"Bearer {INFERENCE_INTERNAL_TOKEN}"}

# Inference healthcheck
class InferenceClient:

    def __init__(self):
        self.base_url = INFERENCE_API_URL

    def healthcheck(self) -> bool:
        response = requests.get(
            f"{self.base_url}/health",
            headers=_auth_headers(),
            timeout=3,
        )
        return response.status_code == 200


def predict(payload: dict):

    response = requests.post(
        f"{INFERENCE_API_URL}/predict",
        json=payload,
        headers=_auth_headers(),
        timeout=5
    )

    response.raise_for_status()
    return response.json()


def get_schema():

    response = requests.get(
        f"{INFERENCE_API_URL}/schema",
        headers=_auth_headers(),
        timeout=5
    )

    response.raise_for_status()
    return response.json()
