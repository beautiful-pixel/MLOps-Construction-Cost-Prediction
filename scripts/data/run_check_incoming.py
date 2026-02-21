import logging
import sys
from pathlib import Path
import os
from utils.logger import setup_logging

from pipelines.data_pipeline.check_incoming import check_and_lock_ready

PROJECT_ROOT_ENV = os.getenv("PROJECT_ROOT")
if not PROJECT_ROOT_ENV:
    raise RuntimeError("PROJECT_ROOT env var is required")
PROJECT_ROOT = Path(PROJECT_ROOT_ENV)

INCOMING_DIR = PROJECT_ROOT / "data" / "incoming"


def main():
    check_and_lock_ready()
    

if __name__ == "__main__":
    setup_logging("check_incoming")
    main()
