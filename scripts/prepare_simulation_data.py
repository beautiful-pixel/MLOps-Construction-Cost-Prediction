"""
Prepare simulation environment with optional linked images.

- Split full tabular dataset into yearly batches
- First batch contains N early years (configurable)
- Remaining batches contain one year each
- Optionally move or copy referenced images into each batch
"""

import argparse
import sys
import shutil
from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SOURCE_TABULAR = PROJECT_ROOT / "data" / "source" / "train_tabular.csv"
SOURCE_IMAGES = PROJECT_ROOT / "data" / "source" / "train_composite"

SIMULATION_DIR = PROJECT_ROOT / "data" / "simulation"
BATCHES_DIR = SIMULATION_DIR / "batches"

IMAGE_COLUMNS = [
    "sentinel2_tiff_file_name",
    "viirs_tiff_file_name",
]


def transfer_linked_images(
    batch_df: pd.DataFrame,
    images_out_dir: Path,
    move: bool,
) -> set[str]:
    """
    Move or copy only images referenced in batch_df.

    Returns the set of successfully transferred filenames.
    """

    images_out_dir.mkdir(parents=True, exist_ok=True)

    referenced_files = set()

    for col in IMAGE_COLUMNS:
        if col in batch_df.columns:
            referenced_files.update(
                batch_df[col].dropna().astype(str).unique()
            )

    transferred = set()

    for filename in referenced_files:
        src = SOURCE_IMAGES / filename
        dst = images_out_dir / filename

        if not src.exists():
            continue

        if move:
            shutil.move(src, dst)
        else:
            shutil.copy2(src, dst)

        transferred.add(filename)

    return transferred


def create_batch(
    batch_name: str,
    batch_df: pd.DataFrame,
    with_images: bool,
    move_images: bool,
) -> None:

    batch_dir = BATCHES_DIR / batch_name
    tabular_dir = batch_dir / "tabular"
    images_dir = batch_dir / "images"

    tabular_dir.mkdir(parents=True, exist_ok=True)

    batch_df = batch_df.copy()

    # Case 1: images disabled → set all image columns to NA
    if not with_images:
        for col in IMAGE_COLUMNS:
            if col in batch_df.columns:
                batch_df[col] = pd.NA

    # Case 2: images enabled
    else:
        transferred = transfer_linked_images(
            batch_df=batch_df,
            images_out_dir=images_dir,
            move=move_images,
        )

        # Replace filenames not successfully transferred with NA
        for col in IMAGE_COLUMNS:
            if col in batch_df.columns:
                batch_df[col] = batch_df[col].apply(
                    lambda x: x if pd.isna(x) or x in transferred else pd.NA
                )

    out_csv = tabular_dir / "train_tabular.csv"
    batch_df.to_csv(out_csv, index=False)

    print(f"{batch_name}: {len(batch_df)} rows")


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--first-batch-years",
        type=int,
        default=2,
        help="Number of early years included in the first batch",
    )

    parser.add_argument(
        "--with-images",
        action="store_true",
        help="Include linked images in batches",
    )

    parser.add_argument(
        "--move-images",
        action="store_true",
        help="Move images instead of copying (only used if --with-images)",
    )

    args = parser.parse_args()

    if not SOURCE_TABULAR.exists():
        print(f"ERROR: {SOURCE_TABULAR} not found.")
        sys.exit(1)

    df = pd.read_csv(SOURCE_TABULAR)

    if "year" not in df.columns:
        print("ERROR: 'year' column missing.")
        sys.exit(1)

    years = sorted(int(y) for y in df["year"].unique())

    BATCHES_DIR.mkdir(parents=True, exist_ok=True)

    # First batch
    first_years = years[:args.first_batch_years]
    first_batch_df = df[df["year"].isin(first_years)]
    first_batch_name = f"batch_{first_years[0]}_{first_years[-1]}"

    create_batch(
        batch_name=first_batch_name,
        batch_df=first_batch_df,
        with_images=args.with_images,
        move_images=args.move_images,
    )

    # Remaining years
    remaining_years = years[args.first_batch_years:]

    for year in remaining_years:
        batch_df = df[df["year"] == year]
        batch_name = f"batch_{year}"

        create_batch(
            batch_name=batch_name,
            batch_df=batch_df,
            with_images=args.with_images,
            move_images=args.move_images,
        )

    print("Simulation batches created successfully.")


if __name__ == "__main__":
    main()