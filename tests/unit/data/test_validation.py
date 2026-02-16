"""
Unit tests for validate_dataframe.

Tests strict schema validation logic.
"""

import pytest
import pandas as pd

from data.validation import validate_dataframe



# Helper: minimal valid config


@pytest.fixture
def valid_config():
    return {
        "target": "construction_cost_per_m2_usd",
        "numeric_features": {
            "deflated_gdp_usd": {},
            "us_cpi": {"impute": "median"},
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
def valid_dataframe():
    return pd.DataFrame({
        "deflated_gdp_usd": [1000.0, 2000.0],
        "us_cpi": [1.2, 1.5],
        "developed_country": ["Yes", "No"],
        "region_economic_classification": [
            "Low income",
            "High income",
        ],
        "year": [2020, 2021],
        "geolocation_name": ["LOC_1", "LOC_2"],
        "country": ["A", "B"],
        "construction_cost_per_m2_usd": [300, 400],
    })


# 1 - Valid dataframe should pass

def test_validate_valid_dataframe(valid_dataframe, valid_config):
    validate_dataframe(valid_dataframe, valid_config)


# 2 - Missing required column

def test_missing_required_column(valid_dataframe, valid_config):
    df = valid_dataframe.drop(columns=["deflated_gdp_usd"])

    with pytest.raises(ValueError):
        validate_dataframe(df, valid_config)


# 3 - Unexpected column in strict mode

def test_unexpected_column_strict(valid_dataframe, valid_config):
    df = valid_dataframe.copy()
    df["unexpected_column"] = 1

    with pytest.raises(ValueError):
        validate_dataframe(df, valid_config, strict_columns=True)


# 4 - Unexpected column non-strict should pass

def test_unexpected_column_non_strict(valid_dataframe, valid_config):
    df = valid_dataframe.copy()
    df["unexpected_column"] = 1

    validate_dataframe(df, valid_config, strict_columns=False)


# 5 - Invalid binary category

def test_invalid_binary_category(valid_dataframe, valid_config):
    df = valid_dataframe.copy()
    df.loc[0, "developed_country"] = "Maybe"

    with pytest.raises(ValueError):
        validate_dataframe(df, valid_config)


# 6 - Invalid ordinal category

def test_invalid_ordinal_category(valid_dataframe, valid_config):
    df = valid_dataframe.copy()
    df.loc[0, "region_economic_classification"] = "Middle income"

    with pytest.raises(ValueError):
        validate_dataframe(df, valid_config)


# 7 - Numeric column wrong dtype

def test_numeric_wrong_dtype(valid_dataframe, valid_config):
    df = valid_dataframe.copy()
    df["deflated_gdp_usd"] = ["not_numeric", "invalid"]

    with pytest.raises(TypeError):
        validate_dataframe(df, valid_config)


# 8 - NaN without imputation should fail

def test_nan_without_impute(valid_dataframe, valid_config):
    df = valid_dataframe.copy()
    df.loc[0, "deflated_gdp_usd"] = None

    with pytest.raises(ValueError):
        validate_dataframe(df, valid_config)


# 9 - NaN allowed if impute configured

def test_nan_allowed_if_impute(valid_dataframe, valid_config):
    df = valid_dataframe.copy()
    df.loc[0, "us_cpi"] = None

    # us_cpi has impute configured
    validate_dataframe(df, valid_config)
