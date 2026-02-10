"""
Schema definition for tabular preprocessing.

Defines feature groups and target column.
"""

TARGET_COL = "construction_cost_per_m2_usd"

KEY_COLUMNS = [
    "sentinel2_tiff_file_name",
    "viirs_tiff_file_name",
]

NUMERIC_FEATURES = [
    "deflated_gdp_usd",
    "us_cpi",
    "year",
    "straight_distance_to_capital_km",
]

BINARY_FEATURES = [
    "developed_country",
    "landlocked",
    "access_to_highway",
    "access_to_railway",
    "access_to_port",
    "access_to_airport",
    "flood_risk_class",
]

ORDINAL_FEATURES = {
    "region_economic_classification": [
        "Low income",
        "Lower-middle income",
        "Upper-middle income",
        "High income",
    ],
    "seismic_hazard_zone": [
        "Low",
        "Moderate",
        "High",
    ],
}

TABULAR_FEATURES = (
    NUMERIC_FEATURES
    + BINARY_FEATURES
    + list(ORDINAL_FEATURES.keys())
)
