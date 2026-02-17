"""
Construction Cost Prediction - Inference API.

Loads the production model from MLflow Model Registry at startup.
Falls back to a local joblib file if MLflow is unavailable.
"""

import os
import logging
from typing import Any, Mapping, Optional

import joblib
import numpy as np
import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient
from mlflow.exceptions import MlflowException, RestException

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
MODEL_NAME = os.getenv("MLFLOW_MODEL_NAME", "construction_cost_model")

BASE_DIR = os.path.dirname(__file__)
FALLBACK_MODEL_PATH = os.path.join(BASE_DIR, "model.joblib")
if not os.path.exists(FALLBACK_MODEL_PATH):
    FALLBACK_MODEL_PATH = os.path.abspath(
        os.path.join(BASE_DIR, "..", "..", "models", "model.joblib")
    )

FEATURE_NAMES = [
    "seismic_hazard_zone_Moderate",
    "koppen_climate_zone_Cwb",
    "tropical_cyclone_wind_risk_Very High",
    "koppen_climate_zone_Dfb",
    "us_cpi",
    "infrastructure_score",
    "landlocked_uncompensated",
    "flood_risk_class_Yes",
    "tropical_cyclone_wind_risk_Moderate",
    "koppen_climate_zone_Am",
    "country_Philippines",
    "koppen_climate_zone_Aw",
    "developed_country_binary",
    "seismic_hazard_zone_Low",
    "straight_distance_to_capital_km",
    "koppen_climate_zone_Dfa",
    "tornadoes_wind_risk_Very Low",
    "region_economic_classification_Lower-middle income",
    "far_no_highway",
    "developed_country_Yes",
    "dev_high_seismic",
    "far_no_railway",
    "distance_infra_interaction",
    "koppen_climate_zone_Cfa",
    "region_economic_classification_Low income",
    "year",
    "dev_high_flood",
    "log_gdp_usd",
    "tropical_cyclone_wind_risk_Low",
]


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

def _load_from_mlflow() -> Optional[Any]:
    """Try to load the Production model from MLflow Model Registry."""
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        client = MlflowClient()

        # Try stages-based lookup
        versions = client.get_latest_versions(MODEL_NAME, stages=["Production"])
        if versions:
            model_uri = f"models:/{MODEL_NAME}/Production"
            logger.info("Loading production model from MLflow: %s", model_uri)
            return mlflow.sklearn.load_model(model_uri)

        # Try alias-based lookup
        try:
            mv = client.get_model_version_by_alias(MODEL_NAME, "prod")
            model_uri = f"models:/{MODEL_NAME}@prod"
            logger.info("Loading model by alias from MLflow: %s", model_uri)
            return mlflow.sklearn.load_model(model_uri)
        except (RestException, MlflowException):
            pass

    except Exception as e:
        logger.warning("Failed to load model from MLflow: %s", e)

    return None


def _load_from_joblib() -> Any:
    """Load model from local joblib file."""
    if not os.path.exists(FALLBACK_MODEL_PATH):
        raise RuntimeError(
            f"No model available. MLflow unreachable and no joblib at {FALLBACK_MODEL_PATH}"
        )
    logger.info("Loading fallback model from %s", FALLBACK_MODEL_PATH)
    loaded = joblib.load(FALLBACK_MODEL_PATH)
    if isinstance(loaded, Mapping) and "model" in loaded:
        loaded = loaded["model"]
    return loaded


# Load model at startup
model = _load_from_mlflow()
if model is None:
    model = _load_from_joblib()
logger.info("Model loaded successfully")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Construction Cost Prediction API",
    description="Predict construction costs per m2 (USD) from tabular features.",
    version="1.0.0",
)


class ConstructionCostFeatures(BaseModel):
    seismic_hazard_zone_moderate: int = Field(..., alias="seismic_hazard_zone_Moderate")
    koppen_climate_zone_cwb: int = Field(..., alias="koppen_climate_zone_Cwb")
    tropical_cyclone_wind_risk_very_high: int = Field(..., alias="tropical_cyclone_wind_risk_Very High")
    koppen_climate_zone_dfb: int = Field(..., alias="koppen_climate_zone_Dfb")
    us_cpi: float
    infrastructure_score: float
    landlocked_uncompensated: int
    flood_risk_class_yes: int = Field(..., alias="flood_risk_class_Yes")
    tropical_cyclone_wind_risk_moderate: int = Field(..., alias="tropical_cyclone_wind_risk_Moderate")
    koppen_climate_zone_am: int = Field(..., alias="koppen_climate_zone_Am")
    country_philippines: int = Field(..., alias="country_Philippines")
    koppen_climate_zone_aw: int = Field(..., alias="koppen_climate_zone_Aw")
    developed_country_binary: int
    seismic_hazard_zone_low: int = Field(..., alias="seismic_hazard_zone_Low")
    straight_distance_to_capital_km: float
    koppen_climate_zone_dfa: int = Field(..., alias="koppen_climate_zone_Dfa")
    tornadoes_wind_risk_very_low: int = Field(..., alias="tornadoes_wind_risk_Very Low")
    region_economic_classification_lower_middle_income: int = Field(
        ..., alias="region_economic_classification_Lower-middle income"
    )
    far_no_highway: int
    developed_country_yes: int = Field(..., alias="developed_country_Yes")
    dev_high_seismic: int
    far_no_railway: int
    distance_infra_interaction: float
    koppen_climate_zone_cfa: int = Field(..., alias="koppen_climate_zone_Cfa")
    region_economic_classification_low_income: int = Field(
        ..., alias="region_economic_classification_Low income"
    )
    year: int
    dev_high_flood: int
    log_gdp_usd: float
    tropical_cyclone_wind_risk_low: int = Field(..., alias="tropical_cyclone_wind_risk_Low")

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "seismic_hazard_zone_Moderate": 1,
                    "koppen_climate_zone_Cwb": 0,
                    "tropical_cyclone_wind_risk_Very High": 1,
                    "koppen_climate_zone_Dfb": 0,
                    "us_cpi": 302.1,
                    "infrastructure_score": 0.62,
                    "landlocked_uncompensated": 0,
                    "flood_risk_class_Yes": 1,
                    "tropical_cyclone_wind_risk_Moderate": 0,
                    "koppen_climate_zone_Am": 0,
                    "country_Philippines": 1,
                    "koppen_climate_zone_Aw": 0,
                    "developed_country_binary": 0,
                    "seismic_hazard_zone_Low": 0,
                    "straight_distance_to_capital_km": 45.7,
                    "koppen_climate_zone_Dfa": 0,
                    "tornadoes_wind_risk_Very Low": 1,
                    "region_economic_classification_Lower-middle income": 1,
                    "far_no_highway": 0,
                    "developed_country_Yes": 0,
                    "dev_high_seismic": 1,
                    "far_no_railway": 0,
                    "distance_infra_interaction": 12.3,
                    "koppen_climate_zone_Cfa": 0,
                    "region_economic_classification_Low income": 0,
                    "year": 2023,
                    "dev_high_flood": 1,
                    "log_gdp_usd": 26.8,
                    "tropical_cyclone_wind_risk_Low": 0,
                }
            ]
        },
    )


@app.post("/predict")
def predict(features: ConstructionCostFeatures):
    """Return a construction cost prediction for the given features."""
    try:
        payload = features.model_dump(by_alias=True)
        input_features = np.array(
            [payload[name] for name in FEATURE_NAMES],
            dtype=float,
        ).reshape(1, -1)

        prediction = model.predict(input_features)
        return {"prediction": float(prediction[0])}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {e}")


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}
