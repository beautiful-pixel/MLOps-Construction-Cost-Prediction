"""
Automated data pipeline:
  1. Detect new CSV batch in data/incoming/
  2. Validate & copy to data/raw/
  3. Preprocess (tabular + satellite features)
  4. Save processed output to data/processed/
  5. DVC-track raw & processed data and auto-commit

Usage:
    # Process whatever is in incoming/
    python scripts/run_ingestion.py

    # Simulate: copy a specific batch into incoming/ then run pipeline
    python scripts/run_ingestion.py --simulate-batch 0

    # Specify satellite image directory
    python scripts/run_ingestion.py --composite-dir D:/GoogleDrive/.../train_composite
"""

import argparse
import logging
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.ingest import ingest_all
from src.data.preprocess import preprocess
import pandas as pd


INCOMING_DIR = PROJECT_ROOT / "data" / "incoming"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
BATCHES_DIR = PROJECT_ROOT / "data" / "batches"
LOGS_DIR = PROJECT_ROOT / "logs"


def setup_logging():
    """Configure logging to both console and timestamped log file."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOGS_DIR / f"ingestion_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logging.info(f"Log file: {log_file}")
    return log_file


def run_dvc_versioning():
    """dvc add raw & processed dirs, then git-add the .dvc files."""
    logging.info("=== DVC versioning ===")
    for target in ("data/raw", "data/processed"):
        logging.info(f"  dvc add {target} ...")
        subprocess.run(
            ["dvc", "add", target],
            cwd=str(PROJECT_ROOT),
            check=True,
        )

    # Stage .dvc files and .gitignore updates for git
    dvc_files = list(PROJECT_ROOT.glob("data/*.dvc")) + list(
        PROJECT_ROOT.glob("data/**/.gitignore")
    )
    if dvc_files:
        subprocess.run(
            ["git", "add"] + [str(f) for f in dvc_files],
            cwd=str(PROJECT_ROOT),
            check=True,
        )
        logging.info(f"  git add: {[f.name for f in dvc_files]}")
    logging.info("  DVC versioning done.")


def simulate_batch(batch_idx: int):
    """Copy a batch file from data/batches/ into data/incoming/."""
    src = BATCHES_DIR / f"batch_{batch_idx}.csv"
    if not src.exists():
        logging.error(f"{src} not found")
        sys.exit(1)
    INCOMING_DIR.mkdir(parents=True, exist_ok=True)
    dest = INCOMING_DIR / src.name
    shutil.copy2(src, dest)
    logging.info(f"Simulated: copied {src.name} -> incoming/")


def main():
    parser = argparse.ArgumentParser(description="Automated data pipeline")
    parser.add_argument(
        "--simulate-batch",
        type=int,
        default=None,
        help="Copy batch_N.csv into incoming/ before running (0-5)",
    )
    parser.add_argument(
        "--composite-dir",
        type=str,
        default=None,
        help="Path to satellite composite TIFFs (optional)",
    )
    parser.add_argument(
        "--no-dvc",
        action="store_true",
        help="Skip DVC versioning step",
    )
    args = parser.parse_args()

    composite_dir = Path(args.composite_dir) if args.composite_dir else None

    log_file = setup_logging()

    # --- simulate batch arrival ---
    if args.simulate_batch is not None:
        simulate_batch(args.simulate_batch)

    # --- step 1: ingest ---
    logging.info("=== Step 1: Ingestion ===")
    ingested = ingest_all(INCOMING_DIR, RAW_DIR, composite_dir)
    if not ingested:
        logging.info("Nothing to process. Exiting.")
        return

    # --- step 2: preprocess each ingested file ---
    logging.info("=== Step 2: Preprocessing ===")
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    for raw_path in ingested:
        logging.info(f"Processing {raw_path.name} ...")
        df = pd.read_csv(raw_path)
        df_processed = preprocess(df, composite_dir)

        out_path = PROCESSED_DIR / raw_path.name
        df_processed.to_csv(out_path, index=False)
        logging.info(f"  Saved -> {out_path}  ({len(df_processed)} rows, {len(df_processed.columns)} cols)")

    # --- step 3: clean incoming/ ---
    for f in INCOMING_DIR.glob("*.csv"):
        f.unlink()
    logging.info("Cleaned incoming/.")

    # --- step 4: DVC versioning ---
    if not args.no_dvc:
        run_dvc_versioning()

    logging.info("Pipeline complete.")


if __name__ == "__main__":
    main()
