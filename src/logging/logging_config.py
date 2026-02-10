import logging
import sys
from datetime import datetime
from pathlib import Path

LOGS_DIR = Path("logs")


def setup_logging(
    run_type: str,
    level: int = logging.INFO,
) -> Path:
    """
    Configure logging global (root logger) avec :
    - console
    - fichier horodaté : <run_type>_YYYYMMDD_HHMMSS.log

    Exemple :
        training_20260210_013359.log
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOGS_DIR / f"{run_type}_{timestamp}.log"

    root_logger = logging.getLogger()

    # Évite les doublons si appelé plusieurs fois (Airflow, tests, etc.)
    if root_logger.handlers:
        root_logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

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
