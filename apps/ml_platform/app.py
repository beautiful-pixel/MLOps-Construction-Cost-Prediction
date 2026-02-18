import os
import requests
import streamlit as st


# Page configuration

st.set_page_config(
    page_title="ML Platform",
    layout="wide"
)


# Configuration

INFERENCE_API_URL = os.getenv(
    "INFERENCE_API_URL",
    "http://localhost:8000"
)


# Title

st.title("ML Platform")


st.markdown(
    """
    Centralized interface for model serving, experiment tracking,
    and platform monitoring.
    """
)


# Platform status

st.subheader("Platform Status")

col1, col2 = st.columns(2)

with col1:

    try:
        response = requests.get(
            f"{INFERENCE_API_URL}/health",
            timeout=3
        )

        if response.status_code == 200:
            health = response.json()

            st.success("Inference API operational")

            st.write("Model version:", health.get("model_version"))
            st.write("Feature version:", health.get("feature_version"))

        else:
            st.warning("Inference API reachable but unhealthy")

    except Exception:
        st.error("Inference API not reachable")


with col2:
    st.info("Training orchestration handled by Airflow")
    st.info("Experiment tracking handled by MLflow")


# Architecture overview

st.subheader("Architecture Overview")

st.markdown(
    """
    This platform integrates the following components:

    - Airflow for data and training orchestration
    - MLflow for experiment tracking and model registry
    - Inference API for model serving
    - Streamlit as unified control interface
    """
)


# Workflow

st.subheader("Workflow")

st.markdown(
    """
    1. Data ingestion and preprocessing  
    2. Model training via Airflow  
    3. Model logging and registration in MLflow  
    4. Model promotion to production  
    5. Online inference via API  
    """
)


# Navigation hint

st.subheader("Navigation")

st.markdown(
    """
    Use the sidebar to access:

    - Inference
    - Experiments
    - Administration
    - Monitoring
    """
)
