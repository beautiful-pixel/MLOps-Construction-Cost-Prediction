import logging
from pathlib import Path
import argparse

from utils.logger import setup_logging
from pipelines.train_pipeline.split import run_split_pipeline


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--version",
        default=None,
        help="Split version to use (e.g. 1). If not specified, active version is used."
    )
    split_version = parser.parse_args().version
    train_df, reference_test_df, cleaned_additional_tests, reference_created = run_split_pipeline(split_version)


if __name__ == "__main__":
    setup_logging("split")
    main()
