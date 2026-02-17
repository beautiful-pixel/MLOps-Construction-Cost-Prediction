import logging
import mlflow

from utils.logger import setup_logging
from utils.mlflow_config import configure_mlflow


def main():
    configure_mlflow()

    with mlflow.start_run() as run:
        run_id = run.info.run_id
        print(f"MLflow run created: {run_id}")

    logging.info("Run closed successfully")


if __name__ == "__main__":
    setup_logging("create_run")
    main()
