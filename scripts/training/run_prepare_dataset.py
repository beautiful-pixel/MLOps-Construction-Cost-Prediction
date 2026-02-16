import argparse
import logging
from pathlib import Path

import pandas as pd

from utils.logging_config import setup_logging
from data.prepare import prepare_training_dataset

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--processed-dir",
        type=str,
        default="data/processed",
        help="Directory containing processed batch CSV files.",
    )
    parser.add_argument(
        "--k-last-batches",
        type=int,
        default=None,
        help="Number of most recent batches to use. "
             "If not provided, all batches are used.",
    )
    parser.add_argument(
        "--output-path",
        type=str,
        default="artifacts/full_dataset.parquet",
        help="Path where the merged dataset will be saved.",
    )

    args = parser.parse_args()

    setup_logging("prepare_dataset")

    processed_dir = PROJECT_ROOT / args.processed_dir
    output_path = PROJECT_ROOT / args.output_path

    logging.info("Preparing dataset from %s", processed_dir)

    if args.k_last_batches is None:
        logging.info("Using all available batches")
    else:
        logging.info("Using %d most recent batches", args.k_last_batches)

    df = prepare_training_dataset(
        processed_dir=processed_dir,
        k_last_batches=args.k_last_batches,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)

    logging.info("Dataset saved to %s", output_path)
    logging.info("Total rows: %d", len(df))


if __name__ == "__main__":
    main()
