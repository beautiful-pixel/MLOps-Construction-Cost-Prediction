"""
Split strategies implementation.

This module contains concrete split algorithms
used by the split dispatcher.
"""

from pathlib import Path
from typing import Tuple, Dict
import pandas as pd



def geographic_split(
    df: pd.DataFrame,
    config: dict,
    version: int,
) -> Tuple[
    pd.DataFrame,
    pd.DataFrame,
    Dict[str, pd.DataFrame],
]:
    """
    Perform geographic split with frozen reference test
    and optional moving test periods.

    Args:
        df (pd.DataFrame): Master dataset.
        config (dict): Split configuration.
        version (int): Split version.

    Returns:
        Tuple[
            pd.DataFrame,
            pd.DataFrame,
            Dict[str, pd.DataFrame]
        ]:
            train_df:
                Training dataset.

            reference_test_df:
                Mandatory frozen reference test dataset.

            additional_tests:
                Dictionary of additional test datasets
                (e.g. {"recent_1_year": df}).

    Raises:
        ValueError:
            If required configuration fields are missing
    """

    # config validation

    required_fields = [
        "geographic_column",
        "periodic_column",
        "test_localities",
        "reference_test_period",
    ]

    for field in required_fields:
        if field not in config:
            raise ValueError(f"'{field}' must be defined in split config.")

    geographic_col = config["geographic_column"]
    periodic_col = config["periodic_column"]
    test_localities = set(config["test_localities"])

    reference_period = config["reference_test_period"]

    if "min" not in reference_period or "max" not in reference_period:
        raise ValueError(
            "reference_test_period must contain 'min' and 'max'."
        )

    min_reference = reference_period["min"]
    max_reference = reference_period["max"]

    test_durations: List[int] = []

    if "moving_test_period" in config:
        moving_cfg = config["moving_test_period"]

        if "durations" in moving_cfg:
            test_durations = moving_cfg["durations"]

            for duration in test_durations:
                if not isinstance(duration, int) or duration <= 0:
                    raise ValueError(
                        f"Invalid duration '{duration}'. "
                        "Must be positive integer."
                    )
    

    # df validation

    if geographic_col not in df.columns:
        raise ValueError(
            f"Geographic column '{geographic_col}' not found."
        )

    if periodic_col not in df.columns:
        raise ValueError(
            f"Periodic column '{periodic_col}' not found."
        )

    
    # Train

    train_df = df[~df[geographic_col].isin(test_localities)].copy()

    # reference test

    reference_test_df = df[
        (df[geographic_col].isin(test_localities)) &
        (df[periodic_col].between(min_reference, max_reference))
    ].copy()

    # additional tests

    additional_tests: Dict[str, pd.DataFrame] = {}
    most_recent_period = df[periodic_col].max()

    for duration in test_durations:

        recent_test = df[
            (df[geographic_col].isin(test_localities)) &
            (df[periodic_col] > most_recent_period - duration)
        ].copy()

        additional_tests[
            f"recent_{duration}_{periodic_col}"
        ] = recent_test


    return train_df, reference_test_df, additional_tests