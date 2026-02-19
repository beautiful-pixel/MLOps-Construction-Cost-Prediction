from typing import Dict

from .airflow_client import airflow_service
from .inference_client import InferenceClient
from .mlflow_client import mlflow_service


class SystemService:

    def __init__(self):
        self.airflow = airflow_service
        self.inference = InferenceClient()
        self.mlflow = mlflow_service

    def check_airflow(self) -> bool:
        try:
            return self.airflow.healthcheck()
        except Exception:
            return False

    def check_inference(self) -> bool:
        try:
            return self.inference.healthcheck()
        except Exception:
            return False

    def check_mlflow(self) -> bool:
        try:
            return self.mlflow.healthcheck()
        except Exception:
            return False

    def get_status(self) -> Dict:
        airflow_ok = self.check_airflow()
        inference_ok = self.check_inference()
        mlflow_ok = self.check_mlflow()

        return {
            "airflow": airflow_ok,
            "inference": inference_ok,
            "mlflow": mlflow_ok,
            "global_status": all([airflow_ok, inference_ok, mlflow_ok]),
        }
