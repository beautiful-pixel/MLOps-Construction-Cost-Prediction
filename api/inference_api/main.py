import os
from typing import Any, Mapping
import joblib
import numpy as np

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field


BASE_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(BASE_DIR, "model.joblib")

if not os.path.exists(MODEL_PATH):
    MODEL_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "models", "model.joblib"))

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

# Chargement du modèle entraîné
try:
    model = joblib.load(MODEL_PATH)
except FileNotFoundError:
    raise RuntimeError(f"Model file not found at {MODEL_PATH}.")
except Exception as e:
    raise RuntimeError(f"Error loading model: {e}")

if isinstance(model, Mapping) and "model" in model:
    model = model["model"]

app = FastAPI(
    title="Construction Cost Prediction API",
    description="A simple API to predict construction costs based on Sentinel-2 satellite imagery.",
    version="1.0.0",
)

# modèle de données pour la requête d'entrée
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

# endpoint de prédiction
@app.post("/predict")
def predict(features: ConstructionCostFeatures):
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
#  endpoint de sante 
@app.get("/health")
def health():
    """Endpoint de santé pour vérifier si l'API est opérationnelle."""
    return {"status": "ok"}
