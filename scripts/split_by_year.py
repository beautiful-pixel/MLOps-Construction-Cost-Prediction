"""
Split train_tabular.csv into 6 yearly batches (2019-2024).

Simulates the arrival of new data over time: each batch represents
one year of construction cost records. Outputs are placed in
data/batches/ and tracked by batch_metadata.csv.

Usage:
    python scripts/split_by_year.py
"""

import os
import sys
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "train_tabular.csv"
BATCHES_DIR = PROJECT_ROOT / "data" / "batches"

PURPOSE_MAP = {
    0: "initial_training",
    1: "new_data_1",
    2: "new_data_2",
    3: "new_data_3",
    4: "new_data_4",
    5: "holdout_test",
}


def main():
    if not RAW_PATH.exists():
        print(f"ERROR: {RAW_PATH} not found.")
        sys.exit(1)

    df = pd.read_csv(RAW_PATH)
    print(f"Loaded {len(df)} rows from {RAW_PATH}")

    BATCHES_DIR.mkdir(parents=True, exist_ok=True)

    years = sorted(df["year"].unique())
    print(f"Years found: {years}")

    metadata_rows = []
    for idx, year in enumerate(years):
        batch_df = df[df["year"] == year].copy()
        out_path = BATCHES_DIR / f"batch_{idx}.csv"
        batch_df.to_csv(out_path, index=False)
        metadata_rows.append({
            "batch": f"batch_{idx}",
            "year": year,
            "n_samples": len(batch_df),
            "purpose": PURPOSE_MAP.get(idx, f"new_data_{idx}"),
        })
        print(f"  batch_{idx}: year={year}, n={len(batch_df)} -> {out_path}")

    meta_df = pd.DataFrame(metadata_rows)
    meta_path = BATCHES_DIR / "batch_metadata.csv"
    meta_df.to_csv(meta_path, index=False)
    print(f"\nMetadata saved to {meta_path}")
    print("Done.")


if __name__ == "__main__":
    main()
