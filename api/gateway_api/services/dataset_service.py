from services.mlflow_client import mlflow_service
from services.airflow_client import airflow_service
from registry.model_registry import get_production_run_id
from registry.run_metadata import get_run_config
from utils.mlflow_config import get_model_name
from prometheus_client import Gauge


DATASET_MASTER_ROWS = Gauge(
    "mlops_dataset_master_rows",
    "Current number of rows in the master dataset",
)

DATASET_NEW_ROWS = Gauge(
    "mlops_dataset_new_rows",
    "New rows since last training run",
)


def compute_dataset_overview(airflow_service):

    model_name = get_model_name()
    prod_run_id = get_production_run_id(model_name)

    if prod_run_id is None:
        return {
            "master_rows": 0,
            "last_training_rows": 0,
            "new_rows": 0,
            "threshold": 10,
            "should_retrain": False,
        }

    prod_config = get_run_config(prod_run_id)

    split_version = prod_config["split_version"]
    feature_version = prod_config["feature_version"]
    model_version = prod_config["model_version"]

    last_master_rows = mlflow_service.get_last_training_master_rows_for_config(
        split_version=split_version,
        feature_version=feature_version,
        model_version=model_version,
    )

    current_master_rows = airflow_service.get_variable(
        "CURRENT_MASTER_ROWS"
    )
    current_master_rows = int(current_master_rows) if current_master_rows else 0

    new_rows = current_master_rows - last_master_rows

    # Export metrics for time-series monitoring (Prometheus)
    DATASET_MASTER_ROWS.set(current_master_rows)
    DATASET_NEW_ROWS.set(new_rows)

    threshold = airflow_service.get_variable(
        "RETRAIN_THRESHOLD_ROWS"
    )

    threshold = int(threshold) if threshold else 10

    should_retrain = new_rows > threshold

    return {
        "master_rows": current_master_rows,
        "last_training_rows": last_master_rows,
        "new_rows": new_rows,
        "threshold": threshold,
        "should_retrain": should_retrain,
    }