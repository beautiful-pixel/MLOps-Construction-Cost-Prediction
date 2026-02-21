"""
Split pipeline orchestration.

This module:
- Loads the master dataset
- Applies a versioned split schema
- Enforces reference test immutability
- Persists split artifacts

Split logic remains pure and isolated from IO.
"""

from pathlib import Path
from typing import Dict
import logging
import time
import pandas as pd

from utils.io import atomic_write_parquet
from splitting.split_schema import get_allowed_split_versions, generate_split


logger = logging.getLogger(__name__)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROCESSED_ROOT = PROJECT_ROOT / "data" / "processed"
REFERENCE_ROOT = PROJECT_ROOT / "data" / "reference" / "tests"
SPLITS_ROOT = PROJECT_ROOT / "data" / "splits"


def run_split_pipeline(split_version: int) -> dict:
    """
    Execute dataset split for a given version.
    """

    start_time = time.time()

    logger.info(f"Starting split pipeline | version=v{split_version}")

    if split_version not in get_allowed_split_versions():
        raise ValueError(
            f"Split version {split_version} not available. "
            f"Allowed versions: {get_allowed_split_versions()}"
        )

    master_path = PROCESSED_ROOT / "master.parquet"

    if not master_path.exists():
        raise ValueError("Master dataset not found.")

    logger.info("Loading master dataset")
    df = pd.read_parquet(master_path)

    master_rows = len(df)

    logger.info(
        f"Generating split version v{split_version} "
        f"(master_rows={master_rows})"
    )

    train_df, reference_candidate_df, additional_tests = generate_split(
        df=df,
        version=split_version,
    )

    if train_df.empty:
        raise ValueError("Generated train split is empty.")

    train_rows = len(train_df)
    reference_candidate_rows = len(reference_candidate_df)

    logger.info(
        f"Train size: {train_rows} | "
        f"Reference candidate size: {reference_candidate_rows}"
    )

    reference_created = False
    reference_dir = REFERENCE_ROOT / f"v{split_version}"
    reference_dir.mkdir(parents=True, exist_ok=True)

    reference_path = reference_dir / "test_reference.parquet"

    if reference_path.exists():

        logger.info("Loading existing frozen reference test")
        reference_test_df = pd.read_parquet(reference_path)

    else:

        logger.info("Creating frozen reference test")

        if reference_candidate_df.empty:
            raise ValueError(
                "Reference test split is empty on first creation."
            )

        reference_test_df = reference_candidate_df.copy()
        reference_test_df.to_parquet(reference_path, index=False)
        reference_created = True

        logger.info(f"Reference test saved at {reference_path}")

    reference_rows = len(reference_test_df)

    logger.info(f"Reference test size: {reference_rows}")

    cleaned_additional_tests: Dict[str, pd.DataFrame] = {}

    for name, test_df in additional_tests.items():

        if test_df.empty:
            logger.warning(
                f"Additional test '{name}' is empty and skipped."
            )
            continue

        cleaned_additional_tests[name] = test_df

    splits_dir = SPLITS_ROOT / f"v{split_version}"
    splits_dir.mkdir(parents=True, exist_ok=True)

    train_path = splits_dir / "train.parquet"
    atomic_write_parquet(train_df, train_path, index=False)

    logger.info(f"Train split saved at {train_path}")

    optional_count = 0
    optional_sizes = {}

    if cleaned_additional_tests:

        optional_dir = splits_dir / "optional_tests"
        optional_dir.mkdir(parents=True, exist_ok=True)

        for name, test_df in cleaned_additional_tests.items():

            test_path = optional_dir / f"{name}.parquet"
            atomic_write_parquet(test_df, test_path, index=False)

            size = len(test_df)
            optional_sizes[name+"_rows"] = size
            optional_count += 1

            logger.info(
                f"Optional test '{name}' saved at {test_path} "
                f"(size={size})"
            )

    duration = round(time.time() - start_time, 2)

    logger.info(f"Split completed in {duration}s")

    return {
        "metrics": {
            "master_rows": master_rows,
            "train_rows": train_rows,
            "reference_rows": reference_rows,
            "optional_test_count": optional_count,
            "split_duration": duration,
            **optional_sizes,
        },
        "params": {
            "reference_created": reference_created,
        }
    }