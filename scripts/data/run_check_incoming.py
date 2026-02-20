import logging
import sys
from pathlib import Path
from utils.logger import setup_logging

from pipelines.data_pipeline.check_incoming import check_and_lock_ready

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INCOMING_DIR = PROJECT_ROOT / "data" / "incoming"


def main():
    check_and_lock_ready()
    

if __name__ == "__main__":
    setup_logging("check_incoming")
    main()
