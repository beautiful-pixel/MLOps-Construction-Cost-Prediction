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
        )

        runs = sorted(
            runs,
            key=lambda r: r.data.metrics.get("reference_rmsle", float("inf"))
        )

        results = []

        for r in runs:

            start_time = r.info.start_time
            end_time = r.info.end_time

            duration_seconds = None
            if start_time and end_time:
                duration_seconds = round((end_time - start_time) / 1000, 2)

            results.append(
                {
                    "run_id": r.info.run_id,
                    "status": r.info.status,
                    "start_time": start_time,   # epoch ms
                    "end_time": end_time,       # epoch ms
                    "run_duration_seconds": duration_seconds,
                    "metrics": r.data.metrics,
                    "params": r.data.params,
                    "tags": r.data.tags,
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

    # Get last master_rows metric for a given training configuration
    def get_last_training_master_rows_for_config(
        self,
        split_version: str,
        feature_version: str,
        model_version: str,
    ) -> int:

        filter_string = (
            f"params.split_version = '{split_version}' and "
            f"params.feature_version = '{feature_version}' and "
            f"params.model_version = '{model_version}'"
        )

        runs = self.client.search_runs(
            experiment_ids=["0"],
            filter_string=filter_string,
            order_by=["attributes.start_time DESC"],
            max_results=1,
        )

        if not runs:
            return 0

        last_run = runs[0]

        master_rows = last_run.data.metrics.get("master_rows")

        if master_rows is None:
            return 0

        return int(master_rows)


# Singleton instance
mlflow_service = MlflowService()
