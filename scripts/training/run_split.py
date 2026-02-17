import logging
import argparse

from utils.logger import setup_logging
from pipelines.train_pipeline.split import run_split_pipeline


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--split-version", type=int, required=True)

    args = parser.parse_args()

    reference_created = run_split_pipeline(
        split_version=args.split_version,
    )

    logging.info(
        f"Split v{args.split_version} completed "
        f"(reference_created={reference_created})"
    )


if __name__ == "__main__":
    setup_logging("split")
    main()
