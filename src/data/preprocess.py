"""
Preprocessing pipeline for construction-cost data.

Tabular: collinearity removal, missing-value imputation, log transforms,
         interaction features, one-hot encoding.
Satellite: spectral index extraction one TIFF at a time (memory-safe).

Adapted from the Solafune baseline project's preprocessing + feature
engineering modules.
"""

import gc
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ------------------------------------------------------------------ #
# Tabular preprocessing                                               #
# ------------------------------------------------------------------ #

COLLINEAR_FEATURES = [
    "access_to_airport",
    "access_to_port",
    "access_to_highway",
    "access_to_railway",
]


def remove_collinear_features(
    df: pd.DataFrame,
    to_remove: Optional[List[str]] = None,
) -> pd.DataFrame:
    """Drop collinear columns (default: access_to_* replaced by
    infrastructure_score created in interaction features)."""
    to_remove = to_remove or COLLINEAR_FEATURES
    present = [c for c in to_remove if c in df.columns]
    return df.drop(columns=present)


def handle_missing_values(
    df: pd.DataFrame,
    strategy: str = "median",
    add_indicators: bool = True,
) -> pd.DataFrame:
    """Impute missing values and optionally add binary indicators."""
    df = df.copy()
    for col in df.columns[df.isnull().any()]:
        if add_indicators:
            df[f"{col}_missing"] = df[col].isnull().astype(int)

        if pd.api.types.is_numeric_dtype(df[col]):
            fill = {"median": df[col].median, "mean": df[col].mean}.get(
                strategy, lambda: 0
            )()
            df[col] = df[col].fillna(fill)
        else:
            mode = df[col].mode()
            df[col] = df[col].fillna(mode.iloc[0] if len(mode) else "Missing")
    return df


def add_log_transforms(df: pd.DataFrame) -> pd.DataFrame:
    """log(deflated_gdp_usd) → log_gdp_usd."""
    df = df.copy()
    if "deflated_gdp_usd" in df.columns:
        df["log_gdp_usd"] = np.log(df["deflated_gdp_usd"].clip(lower=1))
    return df


def create_interaction_features(df: pd.DataFrame) -> pd.DataFrame:
    """Domain-knowledge interaction features (from baseline NB03)."""
    df = df.copy()

    for col in ("developed_country", "landlocked"):
        if col in df.columns:
            df[f"{col}_binary"] = (df[col] == "Yes").astype(int)

    if "developed_country_binary" in df.columns:
        if "seismic_hazard_zone" in df.columns:
            df["dev_high_seismic"] = (
                (df["developed_country_binary"] == 1)
                & (df["seismic_hazard_zone"] == "High")
            ).astype(int)
        if "flood_risk_class" in df.columns:
            df["dev_high_flood"] = (
                (df["developed_country_binary"] == 1)
                & (df["flood_risk_class"] == "Yes")
            ).astype(int)

    access_cols = [
        "access_to_airport",
        "access_to_port",
        "access_to_highway",
        "access_to_railway",
    ]
    if all(c in df.columns for c in access_cols):
        df["infrastructure_score"] = sum(
            (df[c] == "Yes").astype(int) for c in access_cols
        )

    if (
        "straight_distance_to_capital_km" in df.columns
        and "infrastructure_score" in df.columns
    ):
        df["distance_infra_interaction"] = df[
            "straight_distance_to_capital_km"
        ] * (4 - df["infrastructure_score"])

    if (
        "straight_distance_to_capital_km" in df.columns
        and "access_to_highway" in df.columns
    ):
        df["far_no_highway"] = (
            (df["straight_distance_to_capital_km"] > 400)
            & (df["access_to_highway"] == "No")
        ).astype(int)

    if (
        "straight_distance_to_capital_km" in df.columns
        and "access_to_railway" in df.columns
    ):
        df["far_no_railway"] = (
            (df["straight_distance_to_capital_km"] > 400)
            & (df["access_to_railway"] == "No")
        ).astype(int)

    if "landlocked_binary" in df.columns and "access_to_railway" in df.columns:
        df["landlocked_uncompensated"] = (
            (df["landlocked_binary"] == 1)
            & (df["access_to_railway"] == "No")
        ).astype(int)

    return df


def encode_categorical(
    df: pd.DataFrame,
    drop_first: bool = True,
) -> pd.DataFrame:
    """One-hot encode object/category columns (skip ID / file / target cols)."""
    exclude = {
        "construction_cost_per_m2_usd",
        "data_id",
        "sentinel2_tiff_file_name",
        "viirs_tiff_file_name",
        "geolocation_name",
        "quarter_label",
    }
    cat_cols = [
        c
        for c in df.select_dtypes(include=["object", "category"]).columns
        if c not in exclude
    ]
    if not cat_cols:
        return df
    return pd.get_dummies(df, columns=cat_cols, drop_first=drop_first)


# ------------------------------------------------------------------ #
# Satellite feature extraction (memory-safe: 1 TIFF at a time)       #
# ------------------------------------------------------------------ #

BAND_NAMES = [
    "B1", "B2", "B3", "B4", "B5", "B6",
    "B7", "B8", "B8A", "B9", "B11", "B12",
]


def _spectral_indices(band_data: np.ndarray) -> Dict[str, np.ndarray]:
    """Compute spectral indices from (n_bands, H, W) array."""
    bd = {name: band_data[i] for i, name in enumerate(BAND_NAMES)}
    eps = 1e-8
    idx: Dict[str, np.ndarray] = {}

    nir, red, green, blue = bd["B8"], bd["B4"], bd["B3"], bd["B2"]
    swir1, swir2 = bd["B11"], bd["B12"]

    idx["ndvi"] = (nir - red) / (nir + red + eps)
    idx["ndbi"] = (swir1 - nir) / (swir1 + nir + eps)
    idx["ndwi"] = (green - nir) / (green + nir + eps)
    idx["evi"] = 2.5 * (nir - red) / (nir + 6 * red - 7.5 * blue + 1 + eps)
    idx["bsi"] = ((swir1 + red) - (nir + blue)) / (
        (swir1 + red) + (nir + blue) + eps
    )
    idx["ui"] = (swir2 - nir) / (swir2 + nir + eps)
    return idx


def _index_stats(arr: np.ndarray) -> Dict[str, float]:
    """Basic statistics for a 2-D index array."""
    v = arr[np.isfinite(arr)]
    if len(v) == 0:
        return {k: np.nan for k in ("mean", "std", "min", "max", "median", "q25", "q75")}
    return {
        "mean": float(np.mean(v)),
        "std": float(np.std(v)),
        "min": float(np.min(v)),
        "max": float(np.max(v)),
        "median": float(np.median(v)),
        "q25": float(np.percentile(v, 25)),
        "q75": float(np.percentile(v, 75)),
    }


def extract_rs_features_single(tiff_path: Path) -> Dict[str, float]:
    """
    Extract spectral-index statistics from ONE satellite image.

    Memory: loads ~13-18 MB (one TIFF), computes stats, then the caller
    should ``del`` the result / let it go out of scope so GC can reclaim.
    """
    import rasterio

    features: Dict[str, float] = {}
    with rasterio.open(tiff_path) as src:
        band_data = src.read()  # (12, H, W) float — ~13-18 MB

    indices = _spectral_indices(band_data)
    del band_data  # free pixel memory immediately

    for name, arr in indices.items():
        for stat_name, val in _index_stats(arr).items():
            features[f"{name}_{stat_name}"] = val
    del indices
    gc.collect()
    return features


def add_rs_features(
    df: pd.DataFrame,
    composite_dir: Path,
    sentinel_col: str = "sentinel2_tiff_file_name",
) -> pd.DataFrame:
    """
    Append remote-sensing feature columns to df.

    Processes images ONE AT A TIME to stay memory-safe.
    """
    try:
        import rasterio  # noqa: F401
    except ImportError:
        logging.warning("rasterio not installed — skipping satellite features.")
        return df

    records: List[Dict[str, float]] = []
    n = len(df)
    for i, (_, row) in enumerate(df.iterrows()):
        tiff_name = row.get(sentinel_col)
        if pd.isna(tiff_name):
            records.append({})
            continue

        tiff_path = composite_dir / tiff_name
        if not tiff_path.exists():
            records.append({})
            continue

        feats = extract_rs_features_single(tiff_path)
        records.append(feats)

        if (i + 1) % 50 == 0 or i + 1 == n:
            logging.info(f"    RS features: {i + 1}/{n}")

    rs_df = pd.DataFrame(records, index=df.index)
    return pd.concat([df, rs_df], axis=1)


# ------------------------------------------------------------------ #
# Full preprocessing pipeline                                         #
# ------------------------------------------------------------------ #

def preprocess(
    df: pd.DataFrame,
    composite_dir: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Run the full preprocessing pipeline on a raw batch DataFrame.

    1. Interaction features (needs raw access_to_* before removal)
    2. Remove collinear features
    3. Handle missing values
    4. Log transforms
    5. Satellite feature extraction (memory-safe)
    6. One-hot encode categoricals

    Returns the processed DataFrame ready for training / DVC storage.
    """
    logging.info("  [1/6] Creating interaction features ...")
    df = create_interaction_features(df)

    logging.info("  [2/6] Removing collinear features ...")
    df = remove_collinear_features(df)

    logging.info("  [3/6] Handling missing values ...")
    df = handle_missing_values(df)

    logging.info("  [4/6] Adding log transforms ...")
    df = add_log_transforms(df)

    if composite_dir is not None:
        logging.info("  [5/6] Extracting satellite features (1 image at a time) ...")
        df = add_rs_features(df, composite_dir)
    else:
        logging.info("  [5/6] Skipping satellite features (no composite_dir).")

    logging.info("  [6/6] Encoding categoricals ...")
    df = encode_categorical(df)

    gc.collect()
    return df
