"""
Streamlit dashboard for the Construction Cost Prediction MLOps project.

Pages:
1. Project Overview
2. Online Prediction
3. MLflow Experiment Tracking
4. Training Trigger (Airflow)
5. Model Information
"""

import os
import requests
import pandas as pd
import plotly.express as px
import streamlit as st
from mlflow.tracking import MlflowClient
import mlflow

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
AIRFLOW_URL = os.getenv("AIRFLOW_URL", "http://airflow-webserver:8080")
INFERENCE_API_URL = os.getenv("INFERENCE_API_URL", "http://inference-api:8000")
MODEL_NAME = os.getenv("MLFLOW_MODEL_NAME", "construction_cost_model")

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Construction Cost Prediction",
    layout="wide",
)

page = st.sidebar.radio(
    "Navigation",
    [
        "Project Overview",
        "Online Prediction",
        "MLflow Experiments",
        "Trigger Training",
        "Model Info",
    ],
)


# ===================================================================
# Page 1 - Project Overview
# ===================================================================

def page_overview():
    st.title("Construction Cost Prediction - MLOps Dashboard")

    st.markdown(
        """
        ### Project Description

        End-to-end MLOps pipeline for predicting **construction cost per m2
        (USD)** using tabular features and Sentinel-2 satellite imagery.

        ### Architecture

        | Component | Technology |
        |-----------|-----------|
        | Orchestration | Apache Airflow |
        | Experiment tracking | MLflow |
        | Model serving | FastAPI |
        | Dashboard | Streamlit |
        | Database | PostgreSQL |
        | Containerization | Docker Compose |

        ### Data Overview

        - **Training samples**: 1 024
        - **Features**: tabular (economic, geographic, climate indicators)
        - **Satellite imagery**: 2 049 Sentinel-2 GeoTIFFs (12 bands)
        - **Target**: `construction_cost_per_m2_usd`
        - **Time range**: 2019 - 2024 (6 yearly batches)

        ### Pipeline Flow

        ```
        data/incoming/ -> ingest (validate) -> data/raw/
                       -> preprocess -> data/processed/
                       -> split -> train -> evaluate -> promote
        ```
        """
    )


# ===================================================================
# Page 2 - Online Prediction
# ===================================================================

FEATURE_DEFAULTS = {
    "seismic_hazard_zone_Moderate": 0,
    "koppen_climate_zone_Cwb": 0,
    "tropical_cyclone_wind_risk_Very High": 0,
    "koppen_climate_zone_Dfb": 0,
    "us_cpi": 300.0,
    "infrastructure_score": 0.5,
    "landlocked_uncompensated": 0,
    "flood_risk_class_Yes": 0,
    "tropical_cyclone_wind_risk_Moderate": 0,
    "koppen_climate_zone_Am": 0,
    "country_Philippines": 0,
    "koppen_climate_zone_Aw": 0,
    "developed_country_binary": 0,
    "seismic_hazard_zone_Low": 0,
    "straight_distance_to_capital_km": 50.0,
    "koppen_climate_zone_Dfa": 0,
    "tornadoes_wind_risk_Very Low": 0,
    "region_economic_classification_Lower-middle income": 0,
    "far_no_highway": 0,
    "developed_country_Yes": 0,
    "dev_high_seismic": 0,
    "far_no_railway": 0,
    "distance_infra_interaction": 10.0,
    "koppen_climate_zone_Cfa": 0,
    "region_economic_classification_Low income": 0,
    "year": 2023,
    "dev_high_flood": 0,
    "log_gdp_usd": 26.0,
    "tropical_cyclone_wind_risk_Low": 0,
}

FLOAT_FEATURES = {
    "us_cpi", "infrastructure_score", "straight_distance_to_capital_km",
    "distance_infra_interaction", "log_gdp_usd",
}

INT_FEATURES = {"year"}


def page_prediction():
    st.title("Online Prediction")
    st.markdown("Enter feature values below and get a construction cost prediction.")

    col1, col2 = st.columns(2)
    payload = {}

    features_list = list(FEATURE_DEFAULTS.items())
    mid = len(features_list) // 2

    for idx, (name, default) in enumerate(features_list):
        col = col1 if idx < mid else col2
        with col:
            if name in FLOAT_FEATURES:
                payload[name] = st.number_input(name, value=float(default), format="%.2f")
            elif name in INT_FEATURES:
                payload[name] = st.number_input(name, value=int(default), step=1)
            else:
                payload[name] = st.selectbox(name, [0, 1], index=int(default))

    if st.button("Predict", type="primary"):
        try:
            resp = requests.post(
                f"{INFERENCE_API_URL}/predict",
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            result = resp.json()
            st.success(
                f"Predicted construction cost: **${result['prediction']:.2f} / m2**"
            )
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to the inference API. Is the service running?")
        except Exception as e:
            st.error(f"Prediction failed: {e}")


# ===================================================================
# Page 3 - MLflow Experiment Tracking
# ===================================================================

def page_mlflow():
    st.title("MLflow Experiment Tracking")

    try:
        client = MlflowClient()
        experiments = client.search_experiments()
    except Exception as e:
        st.error(f"Cannot connect to MLflow: {e}")
        return

    if not experiments:
        st.info("No experiments found.")
        return

    exp_names = [exp.name for exp in experiments]
    selected_exp = st.selectbox("Select experiment", exp_names)

    exp = next(e for e in experiments if e.name == selected_exp)

    runs = client.search_runs(
        experiment_ids=[exp.experiment_id],
        order_by=["start_time DESC"],
        max_results=50,
    )

    if not runs:
        st.info("No runs found for this experiment.")
        return

    # Build runs table
    rows = []
    for run in runs:
        row = {
            "run_id": run.info.run_id[:8],
            "status": run.info.status,
            "start_time": pd.to_datetime(run.info.start_time, unit="ms"),
        }
        row.update(run.data.params)
        row.update(run.data.metrics)
        rows.append(row)

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)

    # Metrics comparison chart
    metric_cols = [c for c in df.columns if c.startswith(("train_", "reference_"))]
    if metric_cols:
        selected_metric = st.selectbox("Select metric to compare", metric_cols)
        if selected_metric in df.columns:
            chart_df = df[["run_id", selected_metric]].dropna()
            if not chart_df.empty:
                fig = px.bar(
                    chart_df,
                    x="run_id",
                    y=selected_metric,
                    title=f"{selected_metric} across runs",
                )
                st.plotly_chart(fig, use_container_width=True)


# ===================================================================
# Page 4 - Trigger Training DAG
# ===================================================================

def page_trigger():
    st.title("Trigger Training Pipeline")
    st.markdown("Trigger the Airflow `train_pipeline_dag` via REST API.")

    dag_id = st.text_input("DAG ID", value="train_pipeline_dag")

    col1, col2, col3 = st.columns(3)
    with col1:
        split_v = st.number_input("split_version", value=1, min_value=1, step=1)
    with col2:
        feat_v = st.number_input("feature_version", value=1, min_value=1, step=1)
    with col3:
        model_v = st.number_input("model_version", value=1, min_value=1, step=1)

    if st.button("Trigger DAG", type="primary"):
        try:
            resp = requests.post(
                f"{AIRFLOW_URL}/api/v1/dags/{dag_id}/dagRuns",
                json={
                    "conf": {
                        "split_version": split_v,
                        "feature_version": feat_v,
                        "model_version": model_v,
                    }
                },
                auth=("admin", "admin"),
                timeout=30,
            )
            if resp.status_code in (200, 201):
                st.success(
                    f"DAG triggered successfully! "
                    f"Run ID: {resp.json().get('dag_run_id', 'N/A')}"
                )
            else:
                st.error(f"Failed to trigger DAG: {resp.status_code} - {resp.text}")
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to Airflow. Is the webserver running?")
        except Exception as e:
            st.error(f"Error: {e}")


# ===================================================================
# Page 5 - Model Information
# ===================================================================

def page_model_info():
    st.title("Production Model Information")

    try:
        client = MlflowClient()
    except Exception as e:
        st.error(f"Cannot connect to MLflow: {e}")
        return

    # Try stages-based lookup first, then alias-based
    prod_versions = []
    try:
        prod_versions = client.get_latest_versions(MODEL_NAME, stages=["Production"])
    except Exception:
        pass

    if not prod_versions:
        try:
            mv = client.get_model_version_by_alias(MODEL_NAME, "prod")
            prod_versions = [mv]
        except Exception:
            pass

    if not prod_versions:
        st.warning(f"No production model found for '{MODEL_NAME}'.")
        st.info("Train and promote a model first using the training pipeline.")
        return

    mv = prod_versions[0]

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Model Name", MODEL_NAME)
        st.metric("Version", mv.version)
    with col2:
        st.metric("Run ID", mv.run_id[:12] + "...")
        st.metric("Stage", getattr(mv, "current_stage", "Production"))

    # Show metrics from the run
    try:
        run = client.get_run(mv.run_id)
        st.subheader("Metrics")
        metrics = run.data.metrics
        if metrics:
            mcol1, mcol2, mcol3 = st.columns(3)
            for i, (k, v) in enumerate(sorted(metrics.items())):
                with [mcol1, mcol2, mcol3][i % 3]:
                    st.metric(k, f"{v:.4f}")
        else:
            st.info("No metrics recorded for this run.")

        st.subheader("Parameters")
        params = run.data.params
        if params:
            st.json(params)
        else:
            st.info("No parameters recorded for this run.")
    except Exception as e:
        st.error(f"Error loading run details: {e}")


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

PAGES = {
    "Project Overview": page_overview,
    "Online Prediction": page_prediction,
    "MLflow Experiments": page_mlflow,
    "Trigger Training": page_trigger,
    "Model Info": page_model_info,
}

PAGES[page]()
