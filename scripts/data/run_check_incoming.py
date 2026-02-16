"""
Check if new CSV files are present in data/incoming/.

Exit codes:
    0 -> OK (files present OR no files, pipeline safe)
    1 -> Error (directory missing, unexpected issue)

Not used in the current pipeline
"""

import logging
import sys
from pathlib import Path
from utils.logger import setup_logging

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INCOMING_DIR = PROJECT_ROOT / "data" / "incoming"


def main():

    if not INCOMING_DIR.exists():
        logging.error(f"{INCOMING_DIR} does not exist.")
        sys.exit(1)

    csv_files = list(INCOMING_DIR.glob("*.csv"))

    detected_files = len(csv_files)

    if detected_files == 0:
        logging.info("No new files detected in incoming/.")
    else:
        logging.info(f"Detected {len(csv_files)} new file(s):")
        for f in csv_files:
            logging.info(f" - {f.name}")

    logging.info("Incoming check passed.")



if __name__ == "__main__":
    setup_logging("check_incoming")
    main()
