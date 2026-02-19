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
from typing import Dict, Tuple
import logging
import pandas as pd

from utils.io import atomic_write_parquet

from splitting.split_schema import get_allowed_split_versions, generate_split


# Paths

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROCESSED_ROOT = PROJECT_ROOT / "data" / "processed"
REFERENCE_ROOT = PROJECT_ROOT / "data" / "reference" / "tests"
SPLITS_ROOT = PROJECT_ROOT / "data" / "splits"




def run_split_pipeline(split_version: int) -> bool:
    """
    Execute dataset split for a given version.

    Responsibilities:
    - Load master dataset
    - Apply versioned split strategy
    - Enforce reference test immutability
    - Persist split artifacts to disk

    Args:
        split_version (int):
            Validated split configuration version.

    Returns:
        bool:
            True if the reference test set was created
            during this execution, False otherwise.

    Raises:
        ValueError:
            If the split version is invalid,
            the master dataset is missing,
            or generated splits are empty.
    """


    # Validate split version

    if split_version not in get_allowed_split_versions():
        raise ValueError(
            f"Split version {split_version} not available. "
            f"Allowed versions: {get_allowed_split_versions()}"
        )

    # Load master dataset

    master_path = PROCESSED_ROOT / "master.parquet"

    if not master_path.exists():
        raise ValueError("Master dataset not found.")

    logging.info("Loading master dataset")
    df = pd.read_parquet(master_path)


    # Generate splits (pure logic)

    logging.info(f"Generating split version v{split_version}")

    train_df, reference_candidate_df, additional_tests = generate_split(
        df=df,
        version=split_version,
    )

    if train_df.empty:
        raise ValueError("Generated train split is empty.")

    logging.info(f"Train size: {len(train_df)} / Reference test size: {len(reference_candidate_df)}")

    # Handle reference test immutability

    reference_created = False
    reference_dir = REFERENCE_ROOT / f"v{split_version}"
    reference_dir.mkdir(parents=True, exist_ok=True)

    reference_path = reference_dir / "test_reference.parquet"

    if reference_path.exists():
        # Load frozen reference test
        logging.info("Loading existing frozen reference test")
        reference_test_df = pd.read_parquet(reference_path)

    else:
        # First creation
        logging.info("Creating frozen reference test")

        if reference_candidate_df.empty:
            raise ValueError(
                "Reference test split is empty on first creation. "
                "Check split configuration."
            )

        reference_test_df = reference_candidate_df.copy()
        reference_test_df.to_parquet(reference_path, index=False)
        reference_created = True

        logging.info(f"Reference test saved at {reference_path}")

    logging.info(f"Reference test size: {len(reference_test_df)}")


    # Handle additional tests (optional)

    cleaned_additional_tests: Dict[str, pd.DataFrame] = {}

    for name, test_df in additional_tests.items():

        if test_df.empty:
            logging.warning(
                f"Additional test '{name}' is empty and will be skipped."
            )
            continue

        cleaned_additional_tests[name] = test_df


    # Save train and optionnals test dataset

    splits_dir = SPLITS_ROOT / f"v{split_version}"
    splits_dir.mkdir(parents=True, exist_ok=True)
    
    train_path = splits_dir / "train.parquet"
    atomic_write_parquet(train_df, train_path, index=False)

    logging.info(f"Train split saved at {train_path} (size={len(train_df)})")

    if cleaned_additional_tests:

        optional_dir = splits_dir / "optional_tests"
        optional_dir.mkdir(parents=True, exist_ok=True)

        for name, test_df in cleaned_additional_tests.items():

            test_path = optional_dir / f"{name}.parquet"
            atomic_write_parquet(test_df, test_path, index=False)

            logging.info(
                f"Optional test '{name}' saved at {test_path} "
                f"(size={len(test_df)})"
            )

    return reference_created
