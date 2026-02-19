import os
import time
import logging
from typing import Any, Mapping, Literal, List
import joblib
import numpy as np

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from prometheus_client import generate_latest, CollectorRegistry, Counter, Histogram, Gauge


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

# Prometheus metrics
registry = CollectorRegistry()
request_count = Counter("app_requests_total", "Total requests", registry=registry)
prediction_latency = Histogram("app_prediction_latency_seconds", "Prediction latency in seconds", registry=registry)

api_requests_total = Counter(
    "api_requests_total",
    "Total number of API requests",
    ["endpoint", "method", "status_code"],
    registry=registry,
)

api_request_duration_seconds = Histogram(
    "api_request_duration_seconds",
    "API request duration in seconds",
    ["endpoint", "method", "status_code"],
    registry=registry,
)

prediction_value_histogram = Histogram(
    "prediction_value",
    "Distribution des valeurs de prédiction",
    registry=registry,
)

input_feature_count_histogram = Histogram(
    "input_feature_count",
    "Nombre de features dans la requête",
    registry=registry,
)

model_mae_score = Gauge("model_mae_score", "Mean Absolute Error of evaluation batch", registry=registry)
model_rmse_score = Gauge("model_rmse_score", "Root Mean Squared Error of evaluation batch", registry=registry)
model_mape_score = Gauge("model_mape_score", "Mean Absolute Percentage Error of evaluation batch", registry=registry)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("solafune-api")


def _normalize_category(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").replace("-", " ").split())


SEISMIC_HAZARD_MAPPING = {
    "moderate": "seismic_hazard_zone_Moderate",
    "low": "seismic_hazard_zone_Low",
}

KOPPEN_MAPPING = {
    "cwb": "koppen_climate_zone_Cwb",
    "dfb": "koppen_climate_zone_Dfb",
    "am": "koppen_climate_zone_Am",
    "aw": "koppen_climate_zone_Aw",
    "dfa": "koppen_climate_zone_Dfa",
    "cfa": "koppen_climate_zone_Cfa",
}

TROPICAL_CYCLONE_MAPPING = {
    "very high": "tropical_cyclone_wind_risk_Very High",
    "moderate": "tropical_cyclone_wind_risk_Moderate",
    "low": "tropical_cyclone_wind_risk_Low",
}

FLOOD_RISK_MAPPING = {
    "yes": "flood_risk_class_Yes",
}

COUNTRY_MAPPING = {
    "philippines": "country_Philippines",
}

TORNADO_MAPPING = {
    "very low": "tornadoes_wind_risk_Very Low",
}

REGION_MAPPING = {
    "lower middle income": "region_economic_classification_Lower-middle income",
    "low income": "region_economic_classification_Low income",
}

DEVELOPED_COUNTRY_MAPPING = {
    "yes": "developed_country_Yes",
}

class ConstructionCostRawFeatures(BaseModel):
    seismic_hazard_zone: Literal["moderate", "low", "high"]
    koppen_climate_zone: Literal["cwb", "dfb", "am", "aw", "dfa", "cfa"]
    tropical_cyclone_wind_risk: Literal["very high", "moderate", "low"]
    flood_risk_class: Literal["yes", "no"]
    country: Literal["philippines", "Philippines"]
    tornadoes_wind_risk: Literal["very low"]
    region_economic_classification: Literal[
        "low income",
        "lower-middle income",
        "upper-middle income",
        "high income",
    ]
    developed_country: Literal["yes", "no"]
    us_cpi: float
    infrastructure_score: float
    landlocked: Literal["yes", "no"]
    access_to_highway: Literal["yes", "no"]
    access_to_railway: Literal["yes", "no"]
    access_to_port: Literal["yes", "no"]
    access_to_airport: Literal["yes", "no"]
    straight_distance_to_capital_km: float
    distance_infra_interaction: float
    year: int
    dev_high_seismic: int
    dev_high_flood: int
    deflated_gdp_usd: float

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "seismic_hazard_zone": "moderate",
                    "koppen_climate_zone": "cwb",
                    "tropical_cyclone_wind_risk": "very high",
                    "flood_risk_class": "yes",
                    "country": "Philippines",
                    "tornadoes_wind_risk": "very low",
                    "region_economic_classification": "lower-middle income",
                    "developed_country": "no",
                    "us_cpi": 302.1,
                    "infrastructure_score": 0.62,
                    "landlocked": "no",
                    "access_to_highway": "yes",
                    "access_to_railway": "yes",
                    "access_to_port": "yes",
                    "access_to_airport": "yes",
                    "straight_distance_to_capital_km": 45.7,
                    "distance_infra_interaction": 12.3,
                    "year": 2023,
                    "dev_high_seismic": 1,
                    "dev_high_flood": 1,
                    "deflated_gdp_usd": 26.8,
                }
            ]
        },
    )


class EvaluationItem(BaseModel):
    features: ConstructionCostRawFeatures
    true_value: float


def _build_payload_from_raw(raw: ConstructionCostRawFeatures) -> dict[str, float]:
    payload: dict[str, float] = {name: 0.0 for name in FEATURE_NAMES}

    payload["us_cpi"] = raw.us_cpi
    payload["infrastructure_score"] = raw.infrastructure_score
    payload["landlocked_uncompensated"] = 1.0 if raw.landlocked == "yes" else 0.0
    payload["developed_country_binary"] = 1.0 if raw.developed_country == "yes" else 0.0
    payload["straight_distance_to_capital_km"] = raw.straight_distance_to_capital_km
    payload["far_no_highway"] = 0.0 if raw.access_to_highway == "yes" else 1.0
    payload["far_no_railway"] = 0.0 if raw.access_to_railway == "yes" else 1.0
    payload["distance_infra_interaction"] = raw.distance_infra_interaction
    payload["year"] = raw.year
    payload["dev_high_seismic"] = raw.dev_high_seismic
    payload["dev_high_flood"] = raw.dev_high_flood
    payload["log_gdp_usd"] = float(np.log(raw.deflated_gdp_usd))

    seismic_key = SEISMIC_HAZARD_MAPPING.get(_normalize_category(raw.seismic_hazard_zone))
    if seismic_key:
        payload[seismic_key] = 1.0

    koppen_key = KOPPEN_MAPPING.get(_normalize_category(raw.koppen_climate_zone))
    if koppen_key:
        payload[koppen_key] = 1.0

    cyclone_key = TROPICAL_CYCLONE_MAPPING.get(_normalize_category(raw.tropical_cyclone_wind_risk))
    if cyclone_key:
        payload[cyclone_key] = 1.0

    if raw.flood_risk_class == "yes":
        payload["flood_risk_class_Yes"] = 1.0

    country_key = COUNTRY_MAPPING.get(_normalize_category(raw.country))
    if country_key:
        payload[country_key] = 1.0

    tornado_key = TORNADO_MAPPING.get(_normalize_category(raw.tornadoes_wind_risk))
    if tornado_key:
        payload[tornado_key] = 1.0

    region_key = REGION_MAPPING.get(_normalize_category(raw.region_economic_classification))
    if region_key:
        payload[region_key] = 1.0

    if raw.developed_country == "yes":
        payload["developed_country_Yes"] = 1.0

    return payload

# endpoint de prédiction (champs texte bruts)
@app.post("/predict")
def predict(features: ConstructionCostRawFeatures):
    start_time = time.time()
    try:
        payload = _build_payload_from_raw(features)
        input_features = np.array(
            [payload[name] for name in FEATURE_NAMES],
            dtype=float,
        ).reshape(1, -1)

        prediction = model.predict(input_features)

        prediction_value = float(prediction[0])
        prediction_value_histogram.observe(prediction_value)
        input_feature_count_histogram.observe(len(FEATURE_NAMES))

        api_requests_total.labels(endpoint="/predict", method="POST", status_code="200").inc()
        api_request_duration_seconds.labels(
            endpoint="/predict",
            method="POST",
            status_code="200",
        ).observe(time.time() - start_time)
        request_count.inc()
        prediction_latency.observe(time.time() - start_time)

        return {"prediction": prediction_value}

    except Exception as e:
        api_requests_total.labels(endpoint="/predict", method="POST", status_code="500").inc()
        api_request_duration_seconds.labels(
            endpoint="/predict",
            method="POST",
            status_code="500",
        ).observe(time.time() - start_time)
        raise HTTPException(status_code=500, detail=f"Prediction error: {e}")


@app.post("/evaluate")
def evaluate_model(items: List[EvaluationItem]):
    """
    Évalue le modèle sur une liste d'items avec de vraies valeurs.
    Met à jour la métrique Prometheus model_mae_score.
    """
    start_time = time.time()

    if not items:
        raise HTTPException(status_code=400, detail="No items provided for evaluation.")

    predictions: list[float] = []
    truths: list[float] = []

    for item in items:
        try:
            payload = _build_payload_from_raw(item.features)
            input_features = np.array(
                [payload[name] for name in FEATURE_NAMES],
                dtype=float,
            ).reshape(1, -1)
            pred_value = float(model.predict(input_features)[0])
            predictions.append(pred_value)
            truths.append(float(item.true_value))
        except Exception as e:
            logger.error("Error during evaluation item: %s", e)

    if not predictions:
        raise HTTPException(status_code=500, detail="No predictions generated.")

    errors = [p - t for p, t in zip(predictions, truths)]
    abs_errors = [abs(e) for e in errors]
    mae = float(np.mean(abs_errors)) if abs_errors else 0.0
    rmse = float(np.sqrt(np.mean([e * e for e in errors]))) if errors else 0.0
    mape = (
        float(np.mean([abs((t - p) / t) for p, t in zip(predictions, truths) if t != 0.0]))
        if truths
        else 0.0
    )

    model_mae_score.set(mae)
    model_rmse_score.set(rmse)
    model_mape_score.set(mape)

    api_requests_total.labels(endpoint="/evaluate", method="POST", status_code="200").inc()
    api_request_duration_seconds.labels(
        endpoint="/evaluate",
        method="POST",
        status_code="200",
    ).observe(time.time() - start_time)
    request_count.inc()
    prediction_latency.observe(time.time() - start_time)
    logger.info("Model evaluated. MAE: %.4f | RMSE: %.4f | MAPE: %.4f on %d items.", mae, rmse, mape, len(predictions))

    return {
        "message": "Model evaluation completed",
        "mae": mae,
        "rmse": rmse,
        "mape": mape,
        "evaluated_items": len(predictions),
    }
#  endpoint de sante 
@app.get("/health")
def health():
    """Endpoint de santé pour vérifier si l'API est opérationnelle."""
    return {"status": "ok"}


@app.get("/metrics")
async def metrics(request: Request):
    """
    Expose Prometheus metrics.
    """
    return Response(content=generate_latest(registry), media_type="text/plain")