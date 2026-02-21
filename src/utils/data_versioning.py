"""
DVC utilities for dataset versioning.

This module centralizes all dataset snapshot operations
for raw data, master dataset, splits and reference tests.
"""

import subprocess
import logging
from pathlib import Path
import os
import yaml

from typing import Optional, Dict

REPO_ROOT = os.getenv("REPO_ROOT")
if not REPO_ROOT:
    raise RuntimeError("REPO_ROOT environment variable is not defined")

DATA_ROOT = os.getenv("DATA_ROOT")
if not DATA_ROOT:
    raise RuntimeError("DATA_ROOT environment variable is not defined")

REPO_ROOT = Path(REPO_ROOT).resolve()
DATA_ROOT = Path(DATA_ROOT).resolve()


RAW_ROOT = DATA_ROOT / "raw"
PROCESSED_ROOT = DATA_ROOT / "processed"
IMAGES_ROOT = DATA_ROOT / "images"
SPLITS_ROOT = DATA_ROOT / "splits"
REFERENCE_ROOT = DATA_ROOT / "reference" / "tests"


# Core utility

def _dvc_add(path: Path) -> None:
    """
    Run `dvc add` on a given path.

    Args:
        path (Path): File or directory to snapshot.

    Raises:
        RuntimeError: If DVC command fails.
    """


    if not path.exists():
        raise ValueError(f"Path does not exist: {path}")

    try:
        relative_path = path.relative_to(REPO_ROOT)
    except ValueError:
        raise RuntimeError(
            f"Path {path} is not inside REPO_ROOT {REPO_ROOT}"
        )

    logging.info(f"Running: dvc add {relative_path}")

    result = subprocess.run(
        ["dvc", "add", str(relative_path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        logging.error(result.stderr)
        raise RuntimeError(f"DVC add failed for {path}")

    logging.info(f"DVC snapshot completed for {path}")


# Public dataset versioning functions

def dvc_add_raw(batch_id: str) -> None:
    """
    Snapshot a specific raw batch directory.
    """

    batch_path = RAW_ROOT / batch_id

    if not batch_path.exists():
        raise ValueError(f"Raw batch does not exist: {batch_path}")

    logging.info(f"Versioning raw batch: {batch_id}")

    _dvc_add(batch_path)


def dvc_add_master() -> None:
    """
    Snapshot master dataset.
    """
    master_path = PROCESSED_ROOT / "master.parquet"
    _dvc_add(master_path)

def dvc_add_images() -> None:
    """
    Snapshot iamges directory.
    """
    _dvc_add(IMAGES_ROOT)


def dvc_add_split(split_version: int) -> None:
    """
    Snapshot train split directory for a given version.

    Args:
        split_version (int)
    """
    split_dir = SPLITS_ROOT / f"v{split_version}"
    _dvc_add(split_dir)


def dvc_add_reference(split_version: int) -> None:
    """
    Snapshot frozen reference test directory for a given version.

    Args:
        split_version (int)
    """
    reference_dir = REFERENCE_ROOT / f"v{split_version}"
    _dvc_add(reference_dir)


def dvc_add_optional_tests(split_version: int) -> None:
    """
    Snapshot optional test splits if present.

    Args:
        split_version (int)
    """
    optional_dir = SPLITS_ROOT / f"v{split_version}" / "optional_tests"

    if not optional_dir.exists():
        logging.info("No optional tests directory found — skipping DVC snapshot.")
        return

    _dvc_add(optional_dir)

# get hash

def _get_dvc_hash_from_path(path: Path) -> Optional[str]:
    dvc_file = Path(str(path) + ".dvc")

    if not dvc_file.exists():
        return None

    with open(dvc_file, "r") as f:
        content = yaml.safe_load(f)

    return content["outs"][0].get("md5")


def get_images_hash() -> Optional[str]:
    return _get_dvc_hash_from_path(IMAGES_ROOT)


def get_split_hash(split_version: int) -> Optional[str]:
    split_dir = SPLITS_ROOT / f"v{split_version}"
    return _get_dvc_hash_from_path(split_dir)


def get_reference_hash(split_version: int) -> Optional[str]:
    reference_dir = REFERENCE_ROOT / f"v{split_version}"
    return _get_dvc_hash_from_path(reference_dir)

def get_master_hash() -> Optional[str]:
    master_path = PROCESSED_ROOT / "master.parquet"
    return _get_dvc_hash_from_path(master_path)


def get_data_lineage(split_version: int) -> Dict[str, Optional[str]]:
    return {
        "dvc_master_hash": get_master_hash(),
        "dvc_split_hash": get_split_hash(split_version),
        "dvc_reference_hash": get_reference_hash(split_version),
    }  
