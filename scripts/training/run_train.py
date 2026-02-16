import logging
from pathlib import Path
import yaml
import mlflow
import pandas as pd
import argparse

from utils.logging_config import setup_logging
from training.train import train_model


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-name", required=True)
    args = parser.parse_args()

    setup_logging("train")

    train_path = PROJECT_ROOT / "artifacts/train.parquet"
    model_output = PROJECT_ROOT / "models/model.joblib"

    with open(PROJECT_ROOT / "configs/features/v1.yaml") as f:
        feature_config = yaml.safe_load(f)

    with open(PROJECT_ROOT / "configs/model/v1.yaml") as f:
        model_config = yaml.safe_load(f)

    if not train_path.exists():
        raise FileNotFoundError(f"Train dataset not found: {train_path}")

    df = pd.read_parquet(train_path)

    mlflow.set_tracking_uri("http://mlflow:5000")
    mlflow.set_experiment(args.experiment_name)

    with mlflow.start_run(run_name="training_pipeline") as run:
        logging.info("Training started | run_id=%s", run.info.run_id)

        artifacts = train_model(
            train_df=train_df,
            feature_config=feature_config,
            model_config=model_config,
        )

        pipeline = artifacts["pipeline"]
        metrics = artifacts["metrics"]

        # Log params
        mlflow.log_params(artifacts["params"])
        mlflow.log_param("model_type", artifacts["model_type"])
        mlflow.log_param("train_size", artifacts["train_size"])

        # Log metrics
        for k, v in metrics.items():
            mlflow.log_metric(f"train_{k}", v)

        # Save model locally
        joblib.dump(pipeline, model_output)

        # Log model
        mlflow.sklearn.log_model(
            sk_model=pipeline,
            name="model",
        )

        logging.info("Training completed")
        run_id = run.info.run_id

    print(run_id)


if __name__ == "__main__":
    main()
