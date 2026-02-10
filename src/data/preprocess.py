"""
Main preprocessing entrypoint.

Applies tabular preprocessing to raw input data and returns a
model-ready DataFrame.
"""

import logging
import pandas as pd

from .schema import (
    TARGET_COL,
    KEY_COLUMNS,
    TABULAR_FEATURES,
)
from .transformers import build_tabular_preprocessor


def preprocess(df: pd.DataFrame, composite_dir) -> pd.DataFrame:
    """
    Preprocess raw tabular construction-cost data.

    Steps:
    1. Select tabular features
    2. Apply sklearn ColumnTransformer
    3. Rebuild a clean DataFrame with feature names
    4. Re-attach key columns (IDs, filenames)
    5. Keep target column unchanged

    Parameters
    ----------
    df : pd.DataFrame
        Raw input DataFrame loaded from data/raw.

    Returns
    -------
    pd.DataFrame
        Fully preprocessed tabular dataset, ready for training.
    """
    logging.info("Starting tabular preprocessing")

    # --- Safety checks
    missing = set(TABULAR_FEATURES + [TARGET_COL]) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # --- Separate components
    keys_df = df[KEY_COLUMNS].copy() if KEY_COLUMNS else None
    X = df[TABULAR_FEATURES]
    y = df[TARGET_COL]

    # --- Build & apply transformer
    preprocessor = build_tabular_preprocessor()
    X_t = preprocessor.fit_transform(X)

    feature_names = preprocessor.get_feature_names_out()
    X_df = pd.DataFrame(
        X_t,
        columns=feature_names,
        index=df.index,
    )


    # --- Final dataset
    out_df = pd.concat([X_df, y], axis=1)

    logging.info(
        f"Preprocessing complete: {out_df.shape[0]} rows, "
        f"{out_df.shape[1]} columns"
    )

    return out_df
