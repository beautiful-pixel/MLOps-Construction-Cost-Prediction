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
from typing import List
import pandas as pd
import logging

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


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_ROOT = PROJECT_ROOT / "data" / "processed"
IMAGES_ROOT = PROJECT_ROOT / "data" / "images"


def process_linked_images(
    df: pd.DataFrame,
    images_dir: Path,
    images_root: Path,
    data_contract_version: int,
) -> pd.DataFrame:
    """
    Process linked images for a validated batch dataframe.

    Ensures:
    - No missing referenced files
    - No unreferenced files in the batch
    - Technical consistency with the contract
    - Canonical storage and relative path attachment
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

    for name in mapping:
        logging.info(
            f"Canonicalized {len(mapping[name])} linked image(s) "
            f"into {IMAGES_ROOT / name}"
        )

    df = attach_canonical_paths(
        df=df,
        mapping=mapping,
        data_contract_version=data_contract_version,
    )

    return df


def preprocess_batch(
    batch_id: str,
    data_contract_version: int | None = None,
) -> None:
    """
    Preprocess a raw batch and update the master dataset.

    The batch is validated, linked files are processed,
    and the resulting dataframe is merged into master.
    """


    if data_contract_version is None:
        data_contract_version = get_active_data_contract_version()

    if data_contract_version not in get_data_contract_versions():
        raise ValueError(
            f"Data contract version {data_contract_version} not found"
        )

    contract = load_data_contract(data_contract_version)

    raw_batch_dir = RAW_DIR / batch_id
    tabular_dir = raw_batch_dir / "tabular"
    images_dir = raw_batch_dir / "images"

    if not tabular_dir.exists():
        raise FileNotFoundError(f"No tabular directory in {raw_batch_dir}")

    tabular_files = sorted(tabular_dir.glob("*"))

    if not tabular_files:
        raise ValueError(f"No tabular files found in {tabular_dir}")

    # Load and validate all tabular files
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

    # Process linked images

    batch_df = process_linked_images(
        df=batch_df,
        images_dir=images_dir,
        images_root=IMAGES_ROOT,
        data_contract_version=data_contract_version,
    )

    # Merge into master dataset

    PROCESSED_ROOT.mkdir(parents=True, exist_ok=True)
    master_path = PROCESSED_ROOT / "master.parquet"

    if master_path.exists():
        master_df = pd.read_parquet(master_path)
    else:
        master_df = None

    if master_df is not None:
        n_rows_before = len(master_df)

        master_df = merge_into_master(
            batch_df=batch_df,
            master_df=master_df,
            data_contract_version=data_contract_version,
        )

        n_rows_after = len(master_df)
        added = n_rows_after - n_rows_before

        logging.info(
            f"Merged {added} rows out of {len(batch_df)} "
            f"(master {n_rows_before} → {n_rows_after})"
        )
    else:
        master_df = batch_df.copy()
        logging.info(
            f"Initialized master dataset with {len(master_df)} rows."
        )

    atomic_write_parquet(master_df, master_path, index=False)

    logging.info(f"Master dataset updated at {master_path}")
