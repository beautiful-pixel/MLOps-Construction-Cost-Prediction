import requests
import streamlit as st
from streamlit_auth import (
    auth_headers,
    get_auth_token,
    get_gateway_api_url,
    login_sidebar,
)


# Page configuration

st.set_page_config(
    page_title="ML Platform",
    layout="wide"
)


# Configuration

GATEWAY_API_URL = get_gateway_api_url()

login_sidebar()


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
            f"{GATEWAY_API_URL}/health",
            timeout=3
        )
        if response.status_code == 200:
            st.success("Gateway API reachable")
        else:
            st.warning("Gateway API reachable but unhealthy")
    except Exception:
        st.error("Gateway API not reachable")

    if get_auth_token():
        try:
            info_response = requests.get(
                f"{GATEWAY_API_URL}/info",
                headers=auth_headers(),
                timeout=3
            )
            if info_response.status_code == 200:
                info = info_response.json()
                st.success("Authenticated access OK")
                st.write("Model version:", info.get("model_version"))
                st.write("Feature version:", info.get("feature_version"))
                st.write("Split version:", info.get("split_version"))
                if info.get("model_last_updated_at"):
                    st.write("Last updated:", info.get("model_last_updated_at"))
                if info.get("metrics"):
                    st.json(info.get("metrics"))
                if info.get("data_version") is not None:
                    st.write("Data version:", info.get("data_version"))
            elif info_response.status_code in (401, 403):
                st.error("Authentication required. Please login.")
            elif info_response.status_code == 404:
                st.warning("No production model found.")
            else:
                st.warning("Gateway API reachable but unhealthy")
        except Exception:
            st.error("Gateway API not reachable")
    else:
        st.info("Login to view protected system info.")


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
