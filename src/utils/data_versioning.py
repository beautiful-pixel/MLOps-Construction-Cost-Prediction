"""
DVC utilities for dataset versioning.

This module centralizes all dataset snapshot operations
for raw data, master dataset, splits and reference tests.
"""

import subprocess
import logging
from pathlib import Path
import yaml

from typing import Optional, Dict


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_ROOT = PROJECT_ROOT / "data"
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

    logging.info(f"Running: dvc add {path.relative_to(PROJECT_ROOT)}")

    result = subprocess.run(
        ["dvc", "add", str(path.relative_to(PROJECT_ROOT))],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        logging.error(result.stderr)
        raise RuntimeError(f"DVC add failed for {path}")

    logging.info(f"DVC snapshot completed for {path}")


# Public dataset versioning functions

def dvc_add_raw() -> None:
    """
    Snapshot raw data directory.
    """
    _dvc_add(RAW_ROOT)


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


def get_data_lineage(split_version: int) -> Dict[str, Optional[str]]:
    return {
        "dvc_images_hash": get_images_hash(),
        "dvc_split_hash": get_split_hash(split_version),
        "dvc_reference_hash": get_reference_hash(split_version),
    }  
