import logging
import mlflow
import argparse

from utils.logging_config import setup_logging
from models.register import promote_if_better


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--experiment-name", required=True)
    args = parser.parse_args()

    setup_logging("promote")

    mlflow.set_tracking_uri("http://mlflow:5000")
    mlflow.set_experiment(args.experiment_name)

    with mlflow.start_run(run_id=args.run_id):

        promote_if_better(
            run_id=args.run_id,
            model_name="construction_cost_model",
            primary_metric="static_rmsle",
            mode="min",
            data_dvc_rev="unknown",
            split_config_version="v1",
        )

        logging.info("Promotion step completed")


if __name__ == "__main__":
    main()
