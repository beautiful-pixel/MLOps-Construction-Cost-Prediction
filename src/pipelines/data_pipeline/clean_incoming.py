import os
from pathlib import Path
import os
import logging

logger = logging.getLogger(__name__)

DATA_ROOT = os.getenv("DATA_ROOT")
if not DATA_ROOT:
    raise RuntimeError("DATA_ROOT environment variable is not defined")

DATA_ROOT = Path(DATA_ROOT).resolve()
INCOMING_DIR = DATA_ROOT / "incoming"


def clean_incoming() -> None:
    if not INCOMING_DIR.exists():
        raise RuntimeError("Incoming directory does not exist.")

    # Remove processing lock if present
    processing_file = INCOMING_DIR / "_PROCESSING"
    if processing_file.exists():
        processing_file.unlink()
        logger.info("_PROCESSING lock removed.")

    # Remove empty directories only
    for path in sorted(INCOMING_DIR.rglob("*"), reverse=True):
        if path.is_dir():
            try:
                path.rmdir()
                logger.info(f"Removed empty directory: {path}")
            except OSError:
                # Directory not empty → ignore
                pass

    logger.info("Incoming cleanup completed.")
