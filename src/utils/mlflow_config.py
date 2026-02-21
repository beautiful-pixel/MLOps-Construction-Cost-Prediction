import os
import mlflow


def configure_mlflow() -> None:
    """
    Configure MLflow tracking URI and experiment
    from environment variables.
    """

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
    experiment_name = os.getenv("MLFLOW_EXPERIMENT")

    if not tracking_uri:
        raise RuntimeError("MLFLOW_TRACKING_URI is not defined")

    if not experiment_name:
        raise RuntimeError("MLFLOW_EXPERIMENT is not defined")

    mlflow.set_tracking_uri(tracking_uri)

    if mlflow.get_tracking_uri() != tracking_uri:
        raise RuntimeError("MLflow tracking URI not correctly set")

    mlflow.set_experiment(experiment_name)


def get_model_name() -> str:
    name = os.getenv("MLFLOW_MODEL_NAME")
    if not name:
        raise RuntimeError("MLFLOW_MODEL_NAME is not defined")
    return name