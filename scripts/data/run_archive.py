"""
Archive processed batch:

- Move files from data/incoming/ to data/archive/<batch_id>/
- Remove current_batch.txt marker

Not used in the current pipeline since incoming data
is already moved to the raw directory and versioned with DVC.
"""

import logging
import sys
from pathlib import Path
import shutil
from utils.logger import setup_logging

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INCOMING_DIR = PROJECT_ROOT / "data" / "incoming"
ARCHIVE_DIR = PROJECT_ROOT / "data" / "archive"
BATCH_MARKER = PROJECT_ROOT / "data" / "current_batch.txt"


def main():

    if not BATCH_MARKER.exists():
        logging.warning("No current_batch.txt found. Nothing to archive.")
        return

    batch_id = BATCH_MARKER.read_text().strip()

    if not batch_id:
        logging.error("Batch marker empty.")
        sys.exit(1)

    archive_batch_dir = ARCHIVE_DIR / batch_id
    archive_batch_dir.mkdir(parents=True, exist_ok=True)

    logging.info(f"Archiving batch {batch_id}")

    files = list(INCOMING_DIR.glob("*.csv"))

    if not files:
        logging.warning("No files found in incoming/ to archive.")
    else:
        for file in files:
            dest = archive_batch_dir / file.name
            shutil.move(str(file), str(dest))
            logging.info(f"Moved {file.name} -> {archive_batch_dir}")

    # Remove batch marker
    BATCH_MARKER.unlink()
    logging.info("Removed current_batch.txt")

    logging.info("Archive step complete.")


if __name__ == "__main__":
    setup_logging("archive")
    main()
