from pathlib import Path
from datetime import datetime
from uuid import uuid4
import shutil
import logging
import time

from utils.active_config import get_active_data_contract_version
from data.data_contract import get_data_contract_versions, load_data_contract

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
INCOMING_DIR = PROJECT_ROOT / "data" / "incoming"
RAW_DIR = PROJECT_ROOT / "data" / "raw"


def generate_batch_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"batch_{timestamp}_{uuid4().hex[:6]}"


def ingest_incoming_files(
    data_contract_version: int | None = None,
) -> dict | None:
    """
    Ingest incoming tabular and image files into a single raw batch.

    Returns ingestion metrics dictionary or None if nothing to ingest.
    """

    start_time = time.time()

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

    # Detect files
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

    system_files = {"_READY", "_PROCESSING"}

    all_files = {
        file
        for file in INCOMING_DIR.rglob("*")
        if file.is_file()
        and file.name not in system_files
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

    if not tabular_files and not image_files:
        logger.info("No files to ingest.")
        return None

    if image_files and not tabular_files:
        raise ValueError(
            "Images detected without any tabular file."
        )

    logger.info(
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
        logger.info(f"{file.name} -> raw/{batch_id}/tabular/")

    # Move image files
    for file in image_files:
        dest = images_dir / file.name
        shutil.move(str(file), str(dest))

    logger.info(
        f"Moved {len(image_files)} image file(s) "
        f"-> raw/{batch_id}/images/"
    )

    duration = round(time.time() - start_time, 2)

    logger.info(
        f"Ingestion for batch {batch_id} completed in {duration}s."
    )

    return {
        "batch_id": batch_id,
        "tabular_files": len(tabular_files),
        "image_files": len(image_files),
        "ingestion_duration": duration,
    }