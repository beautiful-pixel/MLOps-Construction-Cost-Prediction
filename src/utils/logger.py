import logging
import sys
from datetime import datetime
from pathlib import Path

LOGS_DIR = Path("logs")


def setup_logging(
    run_type: str,
    level: int = logging.INFO,
    subdir: str | None = None,
) -> Path:
    """
    Configure logging global (root logger) avec :
    - console
    - fichier horodaté : <run_type>_YYYYMMDD_HHMMSS.log

    Exemple :
        training_20260210_013359.log
    """

    base_dir = LOGS_DIR

    if subdir:
        base_dir = LOGS_DIR / subdir

    base_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = base_dir / f"{run_type}_{timestamp}.log"

    root_logger = logging.getLogger()

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # If logging already configured (Airflow, pytest, etc.), avoid duplicate console,
    # but ensure a file handler exists for this run.
    if root_logger.handlers:
        existing_files = {
            getattr(handler, "baseFilename", None)
            for handler in root_logger.handlers
        }
        if str(log_file.resolve()) not in existing_files:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        return log_file

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)

    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)

    logging.info(f"Log file initialized: {log_file.resolve()}")

    return log_file
