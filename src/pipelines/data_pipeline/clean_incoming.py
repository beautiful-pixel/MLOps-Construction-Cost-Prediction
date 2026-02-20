from pathlib import Path
import logging

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
INCOMING_DIR = PROJECT_ROOT / "data" / "incoming"


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