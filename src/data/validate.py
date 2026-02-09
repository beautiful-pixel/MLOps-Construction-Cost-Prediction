"""
Schema validation for incoming construction-cost CSV batches
and lightweight satellite image metadata checks.
"""

import pandas as pd
from pathlib import Path
from typing import List, Sequence, Tuple

EXPECTED_COLUMNS = [
    "data_id",
    "geolocation_name",
    "quarter_label",
    "country",
    "year",
    "deflated_gdp_usd",
    "us_cpi",
    "developed_country",
    "landlocked",
    "region_economic_classification",
    "access_to_airport",
    "access_to_port",
    "access_to_highway",
    "access_to_railway",
    "straight_distance_to_capital_km",
    "seismic_hazard_zone",
    "flood_risk_class",
    "tropical_cyclone_wind_risk",
    "tornadoes_wind_risk",
    "koppen_climate_zone",
    "sentinel2_tiff_file_name",
    "viirs_tiff_file_name",
    "construction_cost_per_m2_usd",
]

SENTINEL2_EXPECTED_BANDS = 12


def validate_schema(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """Return (is_valid, list_of_errors) for a tabular CSV."""
    errors: List[str] = []

    missing = set(EXPECTED_COLUMNS) - set(df.columns)
    if missing:
        errors.append(f"Missing columns: {sorted(missing)}")

    if df.empty:
        errors.append("DataFrame is empty")

    if "data_id" in df.columns and df["data_id"].duplicated().any():
        n = int(df["data_id"].duplicated().sum())
        errors.append(f"Duplicate data_id: {n} duplicates")

    if "year" in df.columns and not pd.api.types.is_numeric_dtype(df["year"]):
        errors.append("Column 'year' is not numeric")

    if "construction_cost_per_m2_usd" in df.columns:
        if (df["construction_cost_per_m2_usd"] < 0).any():
            errors.append("Negative values in target column")

    return len(errors) == 0, errors


def validate_tiff_metadata(
    tiff_names: Sequence[str],
    composite_dir: Path,
) -> List[str]:
    """
    Check satellite TIFF metadata WITHOUT loading pixel data.

    Uses rasterio to read only the file header (band count, dimensions).
    Memory cost: near-zero per file.
    """
    try:
        import rasterio
    except ImportError:
        return ["rasterio not installed — skipping TIFF validation"]

    errors: List[str] = []
    for name in tiff_names:
        tiff_path = composite_dir / name
        if not tiff_path.exists():
            errors.append(f"Missing TIFF: {name}")
            continue
        try:
            with rasterio.open(tiff_path) as src:
                if src.count != SENTINEL2_EXPECTED_BANDS:
                    errors.append(
                        f"{name}: expected {SENTINEL2_EXPECTED_BANDS} bands, "
                        f"got {src.count}"
                    )
                if src.width == 0 or src.height == 0:
                    errors.append(f"{name}: zero-size image")
        except Exception as e:
            errors.append(f"{name}: cannot open ({e})")
    return errors
