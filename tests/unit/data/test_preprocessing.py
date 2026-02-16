"""
Unit tests for deterministic preprocessing.
"""

import pandas as pd
import pytest

from data.preprocessing import apply_preprocessing


@pytest.fixture
def base_config():
    return {
        "target": "construction_cost_per_m2_usd",
        "numeric_features": {
            "straight_distance_to_capital_km": {
                "clip": [0, 5000]
            }
        },
        "binary_features": {
            "developed_country": {
                "categories": ["No", "Yes"]
            }
        },
        "ordinal_features": {
            "region_economic_classification": {
                "categories": [
                    "Low income",
                    "Lower-middle income",
                    "Upper-middle income",
                    "High income",
                ]
            }
        },
        "split_columns": [
            "year",
            "geolocation_name",
            "country",
        ],
    }


@pytest.fixture
def base_dataframe():
    return pd.DataFrame({
        "straight_distance_to_capital_km": [100, 200],
        "developed_country": ["No", "Yes"],
        "region_economic_classification": [
            "Low income",
            "High income",
        ],
        "year": [2020, 2021],
        "geolocation_name": ["LOC_1", "LOC_2"],
        "country": ["A", "B"],
        "construction_cost_per_m2_usd": [100, 200],
    })


# 1 - Valid dataframe should be transformed correctly

def test_valid_dataframe(base_dataframe, base_config):

    df_processed = apply_preprocessing(base_dataframe, base_config)

    assert df_processed.loc[0, "developed_country"] == 0
    assert df_processed.loc[1, "developed_country"] == 1

    assert df_processed.loc[0, "region_economic_classification"] == 0
    assert df_processed.loc[1, "region_economic_classification"] == 3


# 2 - Numeric clipping should apply bounds

def test_numeric_clipping(base_dataframe, base_config):

    df = base_dataframe.copy()
    df.loc[0, "straight_distance_to_capital_km"] = -50
    df.loc[1, "straight_distance_to_capital_km"] = 6000

    df_processed = apply_preprocessing(df, base_config)

    assert df_processed.loc[0, "straight_distance_to_capital_km"] == 0
    assert df_processed.loc[1, "straight_distance_to_capital_km"] == 5000


# 3 - Ordinal encoding should respect defined order

def test_ordinal_encoding_order(base_dataframe, base_config):

    df = base_dataframe.copy()
    df.loc[0, "region_economic_classification"] = "Upper-middle income"
    df.loc[1, "region_economic_classification"] = "Lower-middle income"

    df_processed = apply_preprocessing(df, base_config)

    assert df_processed.loc[0, "region_economic_classification"] == 2
    assert df_processed.loc[1, "region_economic_classification"] == 1


# 4 - Split columns should remain unchanged

def test_split_columns_unchanged(base_dataframe, base_config):

    df_processed = apply_preprocessing(base_dataframe, base_config)

    assert df_processed["year"].equals(base_dataframe["year"])
    assert df_processed["geolocation_name"].equals(
        base_dataframe["geolocation_name"]
    )
    assert df_processed["country"].equals(base_dataframe["country"])


# 5 - Target column should remain unchanged

def test_target_column_unchanged(base_dataframe, base_config):

    df_processed = apply_preprocessing(base_dataframe, base_config)

    assert df_processed["construction_cost_per_m2_usd"].equals(
        base_dataframe["construction_cost_per_m2_usd"]
    )
