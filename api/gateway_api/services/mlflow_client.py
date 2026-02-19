# MLflow client service

import os
import requests
from mlflow.tracking import MlflowClient


MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
MODEL_NAME = os.getenv("MLFLOW_MODEL_NAME", "construction_cost_model")


class MlflowService:

    def __init__(self):
        self.client = MlflowClient(tracking_uri=MLFLOW_TRACKING_URI)
        self.base_url = MLFLOW_TRACKING_URI

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


    # List experiments
    def list_experiments(self):
        experiments = self.client.search_experiments()

        return [
            {
                "experiment_id": e.experiment_id,
                "name": e.name,
            }
            for e in experiments
        ]

    # List runs
    def list_runs(self, experiment_id: str):
        runs = self.client.search_runs(
            experiment_ids=[experiment_id],
            order_by=["metrics.reference_rmsle ASC"],
        )

        results = []

        for r in runs:
            results.append(
                {
                    "run_id": r.info.run_id,
                    "status": r.info.status,
                    "metrics": r.data.metrics,
                    "params": r.data.params,
                }
            )

        return results

    # Get current production model (alias-based)
    def get_current_production_model(self):

        mv = self.client.get_model_version_by_alias(
            name=MODEL_NAME,
            alias="prod",
        )

        run = self.client.get_run(mv.run_id)

        return {
            "registered_model_version": mv.version,
            "run_id": mv.run_id,
            "feature_version": run.data.params.get("feature_version"),
            "split_version": run.data.params.get("split_version"),
        }

    # Promote run to production
    def promote_to_production(self, run_id: str):

        # Register model if needed
        mv = self.client.create_model_version(
            name=MODEL_NAME,
            source=f"runs:/{run_id}/model",
            run_id=run_id,
        )

        # Set alias prod
        self.client.set_registered_model_alias(
            name=MODEL_NAME,
            alias="prod",
            version=mv.version,
        )

        return {
            "message": "Model promoted to production",
            "version": mv.version,
        }


# Singleton instance
mlflow_service = MlflowService()
