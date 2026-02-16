"""
Model-level tabular preprocessing.

Handles learned transformations only:
- Numeric imputation
- Numeric clipping
- Categorical imputation
- Categorical encoding (binary, ordinal, onehot)

Does NOT handle:
- Feature engineering
- Image features
"""

from typing import Dict, Any

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    OrdinalEncoder,
    OneHotEncoder,
    FunctionTransformer,
)
from sklearn.impute import SimpleImputer


def build_tabular_model_preprocessor(config: Dict[str, Any]) -> ColumnTransformer:
    """
    Build ColumnTransformer for tabular features only.

    Supports:
    - Numeric: impute + clip
    - Categorical:
        - binary (single column ordinal encoding)
        - ordinal (ordered encoding)
        - onehot
    """

    tabular_cfg = config.get("tabular_features", {})

    transformers = []

    for col, params in tabular_cfg.items():

        feature_type = params.get("type")

        steps = []

        if "impute" in params:
            steps.append(
                (
                    "imputer",
                    SimpleImputer(strategy=params["impute"]),
                )
            )

        if feature_type == "numeric":

            if "clip" in params:
                lower, upper = params["clip"]

                def clip_fn(X, lower=lower, upper=upper):
                    return np.clip(X, lower, upper)

                steps.append(
                    (
                        "clip",
                        FunctionTransformer(clip_fn),
                    )
                )

        elif feature_type == "categorical":

            encoding = params.get("encoding")

            if encoding == "binary":

                steps.append(
                    (
                        "encoder",
                        OrdinalEncoder(),
                    )
                )

            elif encoding == "ordinal":

                steps.append(
                    (
                        "encoder",
                        OrdinalEncoder(categories=[params["order"]]),
                    )
                )

            elif encoding == "onehot":
                steps.append(
                    (
                        "encoder",
                        OneHotEncoder(
                            handle_unknown="ignore",
                            sparse_output=False,
                        ),
                    )
                )

        else:
            raise ValueError(
                f"Unsupported feature type '{feature_type}' for column '{col}'."
            )

        if steps:
            pipeline = Pipeline(steps=steps)
        else:
            transformers.append((col, "passthrough", [col]))
            continue

        transformers.append((col, pipeline, [col]))

    return ColumnTransformer(
        transformers=transformers,
        remainder="drop",
    )
