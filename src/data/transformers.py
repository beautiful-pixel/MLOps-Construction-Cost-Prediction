"""
Sklearn transformers for tabular preprocessing.
"""

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OrdinalEncoder
from sklearn.impute import SimpleImputer

from .schema import (
    NUMERIC_FEATURES,
    BINARY_FEATURES,
    ORDINAL_FEATURES,
)


def build_tabular_preprocessor() -> ColumnTransformer:
    """
    Build the ColumnTransformer for tabular features.

    - Numeric: median imputation
    - Binary: ordinal encoding (No=0, Yes=1)
    - Ordinal: ordered categorical encoding
    """
    return ColumnTransformer(
        transformers=[
            (
                "num",
                SimpleImputer(strategy="median"),
                NUMERIC_FEATURES,
            ),
            (
                "bin",
                OrdinalEncoder(
                    categories=[["No", "Yes"]] * len(BINARY_FEATURES),
                    handle_unknown="use_encoded_value",
                    unknown_value=-1,
                ),
                BINARY_FEATURES,
            ),
            (
                "ord",
                OrdinalEncoder(
                    categories=[
                        ORDINAL_FEATURES[col]
                        for col in ORDINAL_FEATURES
                    ],
                    handle_unknown="use_encoded_value",
                    unknown_value=-1,
                ),
                list(ORDINAL_FEATURES.keys()),
            ),
        ],
        remainder="drop",
    )
