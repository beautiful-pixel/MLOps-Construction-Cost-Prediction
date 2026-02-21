import os
from pathlib import Path
from airflow.exceptions import AirflowSkipException
from datetime import datetime, timedelta
import logging
logger = logging.getLogger(__name__)

DATA_ROOT = os.getenv("DATA_ROOT")
if not DATA_ROOT:
    raise RuntimeError("DATA_ROOT environment variable is not defined")

DATA_ROOT = Path(DATA_ROOT).resolve()
INCOMING_DIR = DATA_ROOT / "incoming"


def check_and_lock_ready(max_processing_age_minutes: int = 20) -> bool:
    """
    Check whether the incoming pipeline can start and lock it if ready.

    Returns:
        True:
            - If a _READY file exists and was successfully renamed to _PROCESSING.

        False:
            - If no _READY file exists (nothing to process).
            - If a _PROCESSING file exists and is recent (pipeline already running).

    Raises:
        RuntimeError:
            - If a _PROCESSING file exists and is older than the allowed threshold
    """

    logger.info("Checking _READY status.")

    ready_file = INCOMING_DIR / "_READY"
    processing_file = INCOMING_DIR / "_PROCESSING"

    # Case 1 — already processing
    if processing_file.exists():

        modified_time = datetime.fromtimestamp(processing_file.stat().st_mtime)
        age = datetime.now() - modified_time

        if age > timedelta(minutes=max_processing_age_minutes):
            raise RuntimeError(
                "_PROCESSING file is too old. Pipeline may be stuck."
            )

        logger.info("Still processing")
        return False

    # Case 2 — nothing to process
    if not ready_file.exists():
        logger.info("No _READY file found in incoming folder")
        return False

    # Case 3 — lock
    logger.info("Locking incoming directory.")
    ready_file.rename(processing_file)
    return True
