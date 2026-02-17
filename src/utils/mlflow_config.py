import os
import mlflow
from dotenv import load_dotenv


def configure_mlflow() -> None:
    """
    Configure MLflow tracking URI and experiment
    from environment variables.
    """


    # Load local .env only if no tracking URI is set
    if "MLFLOW_TRACKING_URI" not in os.environ:
        load_dotenv()

    if "MLFLOW_TRACKING_URI" not in os.environ:
        raise ValueError("MLFLOW_TRACKING_URI is not defined")
    if "MLFLOW_EXPERIMENT" not in os.environ:
        raise ValueError("MLFLOW_EXPERIMENT is not defined")
        
    tracking_uri = os.environ["MLFLOW_TRACKING_URI"]
    experiment_name = os.environ["MLFLOW_EXPERIMENT"]

    mlflow.set_tracking_uri(tracking_uri)

    current_uri = mlflow.get_tracking_uri()
    if current_uri != tracking_uri:
        raise RuntimeError("MLflow tracking URI not correctly set")

    mlflow.set_experiment(experiment_name)



def get_model_name() -> str:
    name = os.getenv("MLFLOW_MODEL_NAME")
    if not name:
        raise ValueError("MLFLOW_MODEL_NAME is not defined")
    return name

