import pandas as pd
from typing import Tuple, List

def location_split_fixed_period(
    df: pd.DataFrame,
    location_col: str,
    year_col: str,
    train_years: List[int],
    test_locations: List[str],
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Location-based split on a fixed historical period.
    """
    df_period = df[df[year_col].isin(train_years)].copy()

    test_df = df_period[df_period[location_col].isin(test_locations)]
    train_df = df_period[~df_period[location_col].isin(test_locations)]

    return train_df, test_df


def recent_evaluation_subset(
    df: pd.DataFrame,
    location_col: str,
    year_col: str,
    test_locations: List[str],
    recent_years: List[int],
) -> pd.DataFrame:
    """
    Non-decisional evaluation on recent data.
    """
    return df[
        (df[location_col].isin(test_locations)) &
        (df[year_col].isin(recent_years))
    ].copy()


import hashlib

def fingerprint_split(
    df,
    id_columns,
):
    """
    Create a stable fingerprint of a split based on logical row identities.
    """
    ids = (
        df[id_columns]
        .astype(str)
        .sort_values(by=id_columns)
        .agg("|".join, axis=1)
        .tolist()
    )

    payload = "\n".join(ids)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
