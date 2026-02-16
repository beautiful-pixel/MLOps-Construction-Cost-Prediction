import logging
from pathlib import Path
import pandas as pd
import joblib
import mlflow
import yaml
import argparse

from utils.logging_config import setup_logging
from training.evaluate import evaluate_model


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--experiment-name", required=True)
    args = parser.parse_args()

    setup_logging("evaluate")

    model_path = PROJECT_ROOT / "models/model.joblib"
    static_path = PROJECT_ROOT / "artifacts/static_test.parquet"
    recent_path = PROJECT_ROOT / "artifacts/recent_test.parquet"

    with open(PROJECT_ROOT / "configs/features/v1.yaml") as f:
        feature_config = yaml.safe_load(f)

    target_col = feature_config["target"]

    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    if not static_path.exists():
        raise FileNotFoundError(f"Static test set not found: {static_path}")

    if not recent_path.exists():
        raise FileNotFoundError(f"Recent test set not found: {recent_path}")

    pipeline = joblib.load(model_path)

    mlflow.set_tracking_uri("http://mlflow:5000")
    mlflow.set_experiment(args.experiment_name)

    with mlflow.start_run(run_id=args.run_id):
        static_df = pd.read_parquet(static_path)
        recent_df = pd.read_parquet(recent_path)

        evaluate_model(
            pipeline=pipeline,
            eval_df=static_df,
            target_col=target_col,
            prefix="static",
            feature_config=feature_config,
        )

        evaluate_model(
            pipeline=pipeline,
            eval_df=recent_df,
            target_col=target_col,
            prefix="recent",
            feature_config=feature_config,
        )

        logging.info("Evaluation completed")


if __name__ == "__main__":
    main()
