import os
import time
import logging
from bisect import bisect_right
from dataclasses import dataclass
from threading import Lock
from typing import Optional, Type
from pydantic import BaseModel

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import Response
from prometheus_client import generate_latest, Counter, Histogram, Gauge

from models.loader import load_production_model
from registry.model_registry import get_model_version_from_alias
from registry.run_metadata import get_run_config
from utils.logger import setup_logging
from inference.schema_builder import build_pydantic_model
from utils.mlflow_config import get_model_name
from features.feature_schema import get_ordered_features, load_feature_schema
from data.data_contract import load_data_contract



# Logging

setup_logging("inference_api")

# Environment configuration

API_TITLE = os.getenv("INFERENCE_API_TITLE", "Inference API")
INFERENCE_INTERNAL_TOKEN = os.getenv("INFERENCE_INTERNAL_TOKEN")

# FastAPI app

app = FastAPI(
    title=API_TITLE,
    version="1.0",
)

# Prometheus metrics

api_requests_total = Counter(
    "api_requests_total",
    "Total number of API requests",
    ["endpoint", "method", "status_code"],
)

api_request_duration_seconds = Histogram(
    "api_request_duration_seconds",
    "API request duration in seconds",
    ["endpoint", "method", "status_code"],
)

predictions_by_category = Counter(
    "predictions_by_category",
    "Number of predictions by category",
    ["category"],
)

prediction_confidence_score_histogram = Histogram(
    "prediction_confidence_score_histogram",
    "Prediction confidence score histogram",
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
)

served_model_version_gauge = Gauge(
    "served_model_version",
    "Model version served",
)


def _record_request_metrics(
    endpoint: str,
    method: str,
    status_code: int,
    start_time: float,
) -> None:
    labels = {
        "endpoint": endpoint,
        "method": method,
        "status_code": str(status_code),
    }
    api_requests_total.labels(**labels).inc()
    api_request_duration_seconds.labels(**labels).observe(
        time.time() - start_time
    )


def _parse_thresholds(raw: str | None) -> list[float]:
    if not raw:
        return []
    thresholds: list[float] = []
    for item in raw.split(","):
        value = item.strip()
        if not value:
            continue
        try:
            thresholds.append(float(value))
        except ValueError:
            logging.warning(
                "Invalid PREDICTION_CATEGORY_THRESHOLDS value: %s", value
            )
            return []
    return sorted(thresholds)


def _resolve_threshold_labels(
    raw: str | None,
    bucket_count: int,
) -> list[str]:
    if raw:
        labels = [label.strip() for label in raw.split(",") if label.strip()]
        if len(labels) == bucket_count:
            return labels
        logging.warning(
            "PREDICTION_CATEGORY_LABELS ignored: expected %d labels, got %d",
            bucket_count,
            len(labels),
        )
    if bucket_count == 3:
        return ["low", "medium", "high"]
    if bucket_count == 4:
        return ["low", "medium", "high", "very_high"]
    return [f"bucket_{idx}" for idx in range(bucket_count)]


PREDICTION_CATEGORY_FIELD = os.getenv(
    "PREDICTION_CATEGORY_FIELD",
    "region_economic_classification",
)
PREDICTION_CATEGORY_THRESHOLDS = _parse_thresholds(
    os.getenv("PREDICTION_CATEGORY_THRESHOLDS")
)
PREDICTION_CATEGORY_LABELS = (
    _resolve_threshold_labels(
        os.getenv("PREDICTION_CATEGORY_LABELS"),
        len(PREDICTION_CATEGORY_THRESHOLDS) + 1,
    )
    if PREDICTION_CATEGORY_THRESHOLDS
    else []
)
CONFIDENCE_MAX_ESTIMATORS = int(
    os.getenv("CONFIDENCE_MAX_ESTIMATORS", "50")
)


def _resolve_prediction_category(
    payload: dict,
    prediction_value: float,
) -> str:
    field_value = payload.get(PREDICTION_CATEGORY_FIELD)
    if field_value not in (None, ""):
        return str(field_value)

    explicit = payload.get("category")
    if explicit not in (None, ""):
        return str(explicit)

    if PREDICTION_CATEGORY_THRESHOLDS:
        bucket_index = bisect_right(
            PREDICTION_CATEGORY_THRESHOLDS,
            prediction_value,
        )
        return PREDICTION_CATEGORY_LABELS[bucket_index]

    return "unknown"


def _unwrap_model_for_confidence(model_obj: object) -> object:
    impl = getattr(model_obj, "_model_impl", None)
    if impl is not None:
        underlying = getattr(impl, "model", None)
        if underlying is not None:
            return underlying
    return model_obj


def _confidence_from_proba(
    model_obj: object,
    input_df: pd.DataFrame,
) -> float | None:
    predict_proba = getattr(model_obj, "predict_proba", None)
    if predict_proba is None:
        return None
    try:
        probabilities = predict_proba(input_df)
    except Exception:
        return None
    if probabilities is None or len(probabilities) == 0:
        return None
    return float(np.max(probabilities[0]))


def _confidence_from_ensemble(
    model_obj: object,
    input_df: pd.DataFrame,
) -> float | None:
    estimators = getattr(model_obj, "estimators_", None)
    if estimators is None:
        return None

    preds: list[float] = []

    def _add_prediction(estimator: object) -> None:
        if estimator is None:
            return
        predict = getattr(estimator, "predict", None)
        if predict is None:
            return
        preds.append(float(predict(input_df)[0]))

    if isinstance(estimators, (list, tuple, np.ndarray)):
        for estimator in estimators:
            if len(preds) >= CONFIDENCE_MAX_ESTIMATORS:
                break
            if isinstance(estimator, (list, tuple, np.ndarray)):
                for sub_estimator in estimator:
                    if len(preds) >= CONFIDENCE_MAX_ESTIMATORS:
                        break
                    _add_prediction(sub_estimator)
            else:
                _add_prediction(estimator)

    if not preds:
        return None

    std = float(np.std(preds))
    return float(np.exp(-std))


def _compute_confidence_score(
    model_obj: object,
    input_df: pd.DataFrame,
) -> float | None:
    base_model = _unwrap_model_for_confidence(model_obj)
    score = _confidence_from_proba(base_model, input_df)
    if score is None:
        score = _confidence_from_ensemble(base_model, input_df)
    if score is None:
        return None
    return float(min(max(score, 0.0), 1.0))


# Global state (loaded at startup)


@dataclass(frozen=True)
class ModelState:
    model: object
    served_model_version: Optional[str]
    run_id: str
    feature_version: int
    feature_order: list[str]
    InputModel: Type[BaseModel]
    target_name: str


_state: Optional[ModelState] = None
_state_lock = Lock()


def _load_state_from_production() -> ModelState:
    model_name = get_model_name()

    loaded_model = load_production_model(model_name=model_name)

    mv = get_model_version_from_alias(model_name, "prod")
    served_version: Optional[str] = None
    if mv is not None:
        served_version = str(mv.version)

    run_id = getattr(loaded_model.metadata, "run_id", None)
    if run_id is None:
        raise RuntimeError("Unable to retrieve run_id from model metadata")

    config = get_run_config(run_id)

    resolved_feature_version = int(config["feature_version"])
    feature_schema = load_feature_schema(resolved_feature_version)
    contract_version = feature_schema["data_contract"]
    data_contract = load_data_contract(contract_version)

    resolved_target_name = data_contract["target"]
    resolved_feature_order = get_ordered_features(resolved_feature_version)
    resolved_input_model = build_pydantic_model(resolved_feature_version)

    return ModelState(
        model=loaded_model,
        served_model_version=served_version,
        run_id=str(run_id),
        feature_version=resolved_feature_version,
        feature_order=resolved_feature_order,
        InputModel=resolved_input_model,
        target_name=str(resolved_target_name),
    )


def _set_state(new_state: Optional[ModelState]) -> None:
    global _state
    with _state_lock:
        _state = new_state


def _refresh_served_model_gauge(state: Optional[ModelState]) -> None:
    if state is None or state.served_model_version is None:
        return
    try:
        served_model_version_gauge.set(float(state.served_model_version))
    except ValueError:
        logging.warning("Model version is not numeric, gauge not set.")


def require_internal_token(authorization: str | None = Header(default=None)):
    if not INFERENCE_INTERNAL_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="INFERENCE_INTERNAL_TOKEN not configured",
        )

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=403, detail="Forbidden")

    token = authorization.split(" ", 1)[1]
    if token != INFERENCE_INTERNAL_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")


# Startup event

@app.on_event("startup")
def startup_event():
    logging.info("Starting inference API initialization")

    try:
        state = _load_state_from_production()
        _set_state(state)
        _refresh_served_model_gauge(state)

        logging.info(
            "Model loaded successfully | run_id=%s | feature_version=%s | model_version=%s",
            state.run_id,
            state.feature_version,
            state.served_model_version,
        )

    except Exception:
        logging.warning("No production model available.")
        _set_state(None)


@app.post("/reload")
def reload_model(internal=Depends(require_internal_token)):
    """Reload the production model (alias 'prod') without restarting the service."""

    start_time = time.time()
    try:
        state = _load_state_from_production()
        _set_state(state)
        _refresh_served_model_gauge(state)
        _record_request_metrics(
            "/reload",
            "POST",
            200,
            start_time,
        )
        return {
            "status": "reloaded",
            "model_version": state.served_model_version,
            "run_id": state.run_id,
            "feature_version": state.feature_version,
        }
    except Exception as exc:
        logging.exception("Reload error")
        _record_request_metrics(
            "/reload",
            "POST",
            500,
            start_time,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Reload failed: {exc}",
        )


# Prediction endpoint

@app.post("/predict")
def predict(payload: dict, internal=Depends(require_internal_token)):

    endpoint = "/predict"
    method = "POST"
    state = _state
    if state is None:
        _record_request_metrics(
            endpoint,
            method,
            503,
            time.time(),
        )
        raise HTTPException(
            status_code=503,
            detail="No production model loaded"
        )

    start_time = time.time()

    try:
        # Validate using dynamic Pydantic model
        validated = state.InputModel(**payload)
        input_dict = validated.model_dump()

        # Use DataFrame to preserve feature alignment
        input_df = pd.DataFrame([input_dict])

        prediction = state.model.predict(input_df)
        prediction_value = float(prediction[0])

        _record_request_metrics(
            endpoint,
            method,
            200,
            start_time,
        )
        category = _resolve_prediction_category(input_dict, prediction_value)
        predictions_by_category.labels(category=str(category)).inc()
        confidence_score = _compute_confidence_score(state.model, input_df)
        if confidence_score is not None:
            prediction_confidence_score_histogram.observe(confidence_score)

        return {
            "prediction": prediction_value,
            "model_version": state.served_model_version
        }

    except Exception:
        logging.exception("Prediction error")
        _record_request_metrics(
            endpoint,
            method,
            500,
            start_time,
        )
        raise HTTPException(
            status_code=500,
            detail="Prediction failed"
        )


def _build_health_payload() -> dict:
    state = _state
    if state is None:
        return {
            "status": "no_model_loaded",
            "message": "Il n'y a pas de modèle actuellement.",
        }
    return {
        "status": "ok",
        "model_version": state.served_model_version or "unknown"
    }


@app.get("/info")
def info(internal=Depends(require_internal_token)):
    start_time = time.time()
    payload = _build_health_payload()
    _record_request_metrics(
        "/info",
        "GET",
        200,
        start_time,
    )
    return payload

@app.get("/health")
def health(internal=Depends(require_internal_token)):
    return _build_health_payload()


# Prometheus metrics endpoint
@app.get("/metrics")
def metrics():
    return Response(
        generate_latest(),
        media_type="text/plain"
    )

# Schema endpoint
@app.get("/schema")
def get_schema(internal=Depends(require_internal_token)):
    state = _state
    if state is None:
        raise HTTPException(status_code=503, detail="Model not initialized")


    return {
        "model_version": state.served_model_version,
        "target": state.target_name,
        "input_schema": state.InputModel.model_json_schema(),
    }