import argparse
import logging

from utils.logger import setup_logging
from pipelines.train_pipeline.evaluate import evaluate_model
from utils.mlflow_config import configure_mlflow


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--run-id", required=True)
    parser.add_argument("--split-version", type=int, required=True)
    parser.add_argument("--feature-version", type=int, required=True)

    args = parser.parse_args()

    configure_mlflow()

    evaluate_model(
        run_id=args.run_id,
        split_version=args.split_version,
        feature_version=args.feature_version,
    )


if __name__ == "__main__":
    setup_logging("evaluate")
    main()
