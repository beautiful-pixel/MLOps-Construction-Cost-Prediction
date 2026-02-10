"""
Data ingestion: detect new CSV batch files in incoming/, validate schema
and satellite image metadata (without loading pixel data), then register
into raw/.
"""

import gc
import logging
import shutil
import pandas as pd
from pathlib import Path
from typing import List, Optional

from src.data.validate import validate_schema, validate_tiff_metadata


def scan_incoming(incoming_dir: Path) -> List[Path]:
    """Return CSV files found in incoming_dir."""
    if not incoming_dir.exists():
        return []
    return sorted(incoming_dir.glob("*.csv"))


def ingest_file(
    csv_path: Path,
    raw_dir: Path,
    composite_dir: Optional[Path] = None,
) -> Path:
    """
    Validate a single CSV (+ optional TIFF metadata check) and copy to raw/.

    For satellite images we only read rasterio metadata (band count,
    dimensions) — pixel data is never loaded, so memory usage is near-zero.
    """
    df = pd.read_csv(csv_path)

    # --- tabular validation ---
    ok, errors = validate_schema(df)
    if not ok:
        raise ValueError(
            f"Validation failed for {csv_path.name}: {'; '.join(errors)}"
        )

    # --- lightweight TIFF metadata check (no pixel data loaded) ---
    if composite_dir is not None and "sentinel2_tiff_file_name" in df.columns:
        tiff_names = df["sentinel2_tiff_file_name"].dropna().unique()
        tiff_errors = validate_tiff_metadata(tiff_names, composite_dir)
        if tiff_errors:
            for e in tiff_errors:
                logging.warning(f"    TIFF: {e}")

    raw_dir.mkdir(parents=True, exist_ok=True)
    dest = raw_dir / csv_path.name
    shutil.copy2(csv_path, dest)
    return dest


def ingest_all(
    incoming_dir: Path,
    raw_dir: Path,
    composite_dir: Optional[Path] = None,
) -> List[Path]:
    """Scan incoming/, validate each file, copy to raw/."""
    files = scan_incoming(incoming_dir)
    if not files:
        logging.info("No new files in incoming/.")
        return []

    ingested: List[Path] = []
    for f in files:
        logging.info(f"  Ingesting {f.name} ...")
        try:
            dest = ingest_file(f, raw_dir, composite_dir)
            ingested.append(dest)
            logging.info(f"  Ingesting {f.name} ... OK")
        except ValueError as e:
            logging.warning(f"  Ingesting {f.name} ... SKIPPED ({e})")
        finally:
            gc.collect()
    return ingested
