# Airflow client service

import os
import requests
from typing import Dict


AIRFLOW_URL = os.getenv("AIRFLOW_URL", "http://airflow-webserver:8080")
AIRFLOW_USER = os.getenv("AIRFLOW_USER", "admin")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "admin")


class AirflowService:

    def __init__(self):
        self.base_url = AIRFLOW_URL

    # Basic auth
    def _auth(self):
        return (AIRFLOW_USER, AIRFLOW_PASSWORD)

    # Healthcheck
    def healthcheck(self) -> bool:
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=3,
            )
            return response.status_code == 200
        except Exception:
            return False

    # List dags
    def list_dags(self):
        response = requests.get(
            f"{self.base_url}/api/v1/dags",
            auth=self._auth(),
            timeout=5,
        )
        response.raise_for_status()
        return response.json()

    # Trigger dag with optional conf
    def trigger_dag(self, dag_id: str, conf: Dict | None = None):
        response = requests.post(
            f"{self.base_url}/api/v1/dags/{dag_id}/dagRuns",
            json={"conf": conf or {}},
            auth=self._auth(),
            timeout=5,
        )
        response.raise_for_status()
        return response.json()

    # List dag runs
    def list_dag_runs(self, dag_id: str):
        response = requests.get(
            f"{self.base_url}/api/v1/dags/{dag_id}/dagRuns",
            auth=self._auth(),
            timeout=5,
        )
        response.raise_for_status()
        return response.json()

    # List task instances
    def list_task_instances(self, dag_id: str, dag_run_id: str):
        response = requests.get(
            f"{self.base_url}/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances",
            auth=self._auth(),
            timeout=5,
        )
        response.raise_for_status()
        return response.json()


    def get_variable(self, key: str):
        response = requests.get(
            f"{self.base_url}/api/v1/variables/{key}",
            auth=self._auth(),
            timeout=5,
        )

        if response.status_code == 404:
            return None

        response.raise_for_status()
        return response.json()["value"]


    def set_variable(self, key: str, value: str):

        # Try update first
        response = requests.patch(
            f"{self.base_url}/api/v1/variables/{key}",
            json={"value": value},
            auth=self._auth(),
            timeout=5,
        )

        # If variable does not exist, create it
        if response.status_code in (400, 404):
            response = requests.post(
                f"{self.base_url}/api/v1/variables",
                json={
                    "key": key,
                    "value": value,
                },
                auth=self._auth(),
                timeout=5,
            )

        response.raise_for_status()
        return response.json()

# Singleton
airflow_service = AirflowService()
