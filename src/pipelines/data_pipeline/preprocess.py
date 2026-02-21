"""
Batch preprocessing pipeline.

For a given raw batch, this module:

- Validates tabular data against the data contract
- Processes linked external files
- Canonicalizes images
- Merges validated data into the master dataset

Master writes are performed atomically.
"""

from pathlib import Path
import os
import pandas as pd
import logging
import time

from utils.active_config import get_active_data_contract_version
from utils.io import atomic_write_parquet, load_tabular_file
from data.data_contract import (
    validate_dataframe,
    get_data_contract_versions,
    load_data_contract,
)
from data.merge import merge_into_master
from data.linked_files import (
    collect_linked_files_by_name,
    validate_image_files_technical,
    canonicalize_linked_images,
    attach_canonical_paths
)

logger = logging.getLogger(__name__)

PROJECT_ROOT_ENV = os.getenv("PROJECT_ROOT")
if not PROJECT_ROOT_ENV:
    raise RuntimeError("PROJECT_ROOT env var is required")
PROJECT_ROOT = Path(PROJECT_ROOT_ENV)
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_ROOT = PROJECT_ROOT / "data" / "processed"
IMAGES_ROOT = PROJECT_ROOT / "data" / "images"


def process_linked_images(
    df: pd.DataFrame,
    images_dir: Path,
    images_root: Path,
    data_contract_version: int,
) -> tuple[pd.DataFrame, int]:
    """
    Process linked images for a validated batch dataframe.
    Returns updated dataframe and number of images processed.
    """

    available_files = {p.name for p in images_dir.glob("*")}

    files_by_name = collect_linked_files_by_name(
        df=df,
        available_files=list(available_files),
        data_contract_version=data_contract_version,
    )

    referenced_files = {
        filename
        for filenames in files_by_name.values()
        for filename in filenames
    }

    unused_files = available_files - referenced_files

    if unused_files:
        raise ValueError(
            "Unreferenced image files detected in batch:\n"
            + "\n".join(sorted(unused_files))
        )

    validate_image_files_technical(
        images_dir=images_dir,
        files_by_name=files_by_name,
        data_contract_version=data_contract_version,
    )

    mapping = canonicalize_linked_images(
        images_dir=images_dir,
        images_root=images_root,
        files_by_name=files_by_name,
        use_hardlink=True,
    )

    images_processed = sum(len(v) for v in mapping.values())

    for name in mapping:
        logger.info(
            f"Canonicalized {len(mapping[name])} linked image(s) "
            f"into {IMAGES_ROOT / name}"
        )

    df = attach_canonical_paths(
        df=df,
        mapping=mapping,
        data_contract_version=data_contract_version,
    )

    return df, images_processed


def preprocess_batch(
    batch_id: str,
    data_contract_version: int | None = None,
) -> dict:
    """
    Preprocess a raw batch and update the master dataset.

    Returns metrics dictionary for monitoring.
    """

    start_time = time.time()

    if data_contract_version is None:
        data_contract_version = get_active_data_contract_version()

    if data_contract_version not in get_data_contract_versions():
        raise ValueError(
            f"Data contract version {data_contract_version} not found"
        )

    raw_batch_dir = RAW_DIR / batch_id
    tabular_dir = raw_batch_dir / "tabular"
    images_dir = raw_batch_dir / "images"

    if not tabular_dir.exists():
        raise FileNotFoundError(f"No tabular directory in {raw_batch_dir}")

    tabular_files = sorted(tabular_dir.glob("*"))

    if not tabular_files:
        raise ValueError(f"No tabular files found in {tabular_dir}")

    # Load and validate tabular files
    validated_dfs = []

    for file in tabular_files:
        df = load_tabular_file(file)
        validate_dataframe(
            df,
            data_contract_version=data_contract_version,
            strict_columns=True,
        )
        validated_dfs.append(df)

    batch_df = pd.concat(validated_dfs, ignore_index=True)
    rows_batch = len(batch_df)

    logger.info(f"Batch {batch_id} contains {rows_batch} rows.")

    # Process images
    batch_df, images_processed = process_linked_images(
        df=batch_df,
        images_dir=images_dir,
        images_root=IMAGES_ROOT,
        data_contract_version=data_contract_version,
    )

    logger.info(
        f"Batch {batch_id} processed {images_processed} image(s)."
    )

    # Merge into master
    PROCESSED_ROOT.mkdir(parents=True, exist_ok=True)
    master_path = PROCESSED_ROOT / "master.parquet"

    if master_path.exists():
        master_df = pd.read_parquet(master_path)
        n_rows_before = len(master_df)

        master_df = merge_into_master(
            batch_df=batch_df,
            master_df=master_df,
            data_contract_version=data_contract_version,
        )

        n_rows_after = len(master_df)
        rows_added = n_rows_after - n_rows_before

        logger.info(
            f"Merged {rows_added} rows "
            f"(master {n_rows_before} → {n_rows_after})."
        )
    else:
        master_df = batch_df.copy()
        rows_added = rows_batch
        logger.info(
            f"Initialized master dataset with {rows_added} rows."
        )

    atomic_write_parquet(master_df, master_path, index=False)

    duration = round(time.time() - start_time, 2)

    logger.info(
        f"Master dataset updated at {master_path} "
        f"in {duration}s."
    )

    return {
        "batch_id": batch_id,
        "rows_batch": rows_batch,
        "rows_added": rows_added,
        "images_processed": images_processed,
        "preprocess_duration": duration,
    }
