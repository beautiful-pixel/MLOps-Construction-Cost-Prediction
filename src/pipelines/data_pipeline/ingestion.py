"""
Ingestion utilities.

Each CSV file inside data/incoming/ becomes its own batch:

incoming/file.csv
    ↓
raw/<batch_id>/file.csv

Returns:
    List[str]: Created batch IDs.
"""

from pathlib import Path
from datetime import datetime
from uuid import uuid4
from typing import List
import shutil
import logging
from utils.active_config import get_active_data_contract_version
from data.data_contract import get_data_contract_versions, load_data_contract

PROJECT_ROOT = Path(__file__).resolve().parents[3]
INCOMING_DIR = PROJECT_ROOT / "data" / "incoming"
RAW_DIR = PROJECT_ROOT / "data" / "raw"


def generate_batch_id() -> str:
    """
    Generate a unique batch ID.

    Format:
        batch_YYYYMMDD_HHMMSS_<random>
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"batch_{timestamp}_{uuid4().hex[:6]}"


def ingest_incoming_files(
    data_contract_version: int | None = None,
) -> str | None:
    """
    Ingest incoming tabular and image files into a single raw batch.

    Files are detected recursively based on extensions defined
    in the specified data contract version. All detected files
    are moved into:

        raw/<batch_id>/
            ├── tabular/
            └── images/

    Behavior:
    - Returns None if no files are found.
    - Raises ValueError if images are present without any tabular file.
    - Raises ValueError if unknown files are present in incoming.
    - Returns the created batch_id if ingestion occurs.

    Parameters
    ----------
    data_contract_version : int | None
        Data contract version to use. If None, the active version is resolved.

    Returns
    -------
    str | None
        The created batch ID if files were ingested,
        otherwise None.

    Raises
    ------
    FileNotFoundError
        If the incoming directory does not exist.
    ValueError
        If the contract version is invalid, images are ingested alone,
        or unknown files are present in incoming.
    """

    # Resolve contract version

    if data_contract_version is None:
        data_contract_version = get_active_data_contract_version()

    if data_contract_version not in get_data_contract_versions():
        raise ValueError(
            f"Data contract version {data_contract_version} not found"
        )

    data_contract = load_data_contract(data_contract_version)
    tabular_extensions = data_contract.get("tabular_extensions", [])
    image_extensions = data_contract.get("image_extensions", [])

    if not INCOMING_DIR.exists():
        raise FileNotFoundError("Incoming directory missing.")

    # Detect files recursively

    tabular_files = [
        file
        for ext in tabular_extensions
        for file in INCOMING_DIR.rglob(f"*.{ext}")
        if file.is_file()
    ]

    image_files = [
        file
        for ext in image_extensions
        for file in INCOMING_DIR.rglob(f"*.{ext}")
        if file.is_file()
    ]

    tabular_files = sorted(tabular_files)
    image_files = sorted(image_files)

    # Detect unknown files

    recognized_files = set(tabular_files) | set(image_files)

    all_files = {
        file
        for file in INCOMING_DIR.rglob("*")
        if file.is_file()
    }

    unknown_files = all_files - recognized_files

    if unknown_files:
        unknown_list = "\n".join(
            str(f.relative_to(INCOMING_DIR))
            for f in sorted(unknown_files)
        )
        raise ValueError(
            "Unknown files detected in incoming:\n"
            f"{unknown_list}"
        )

    # Nothing to ingest

    if not tabular_files and not image_files:
        logging.info("No files to ingest.")
        return None

    if image_files and not tabular_files:
        raise ValueError(
            "Images detected without any tabular file."
        )

    logging.info(
        f"Found {len(tabular_files)} tabular file(s) "
        f"and {len(image_files)} image file(s) to ingest."
    )

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    batch_id = generate_batch_id()
    batch_raw_dir = RAW_DIR / batch_id
    tabular_dir = batch_raw_dir / "tabular"
    images_dir = batch_raw_dir / "images"

    tabular_dir.mkdir(parents=True, exist_ok=False)
    images_dir.mkdir(parents=True, exist_ok=False)

    # Move tabular files

    for file in tabular_files:
        dest = tabular_dir / file.name
        shutil.move(str(file), str(dest))
        logging.info(f"{file.name} -> raw/{batch_id}/tabular/")

    # Move image files

    for file in image_files:
        dest = images_dir / file.name
        shutil.move(str(file), str(dest))
    
    logging.info(f"all the images founded -> raw/{batch_id}/images/")

    return batch_id
