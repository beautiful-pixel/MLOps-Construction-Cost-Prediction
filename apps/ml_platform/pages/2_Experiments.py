# Experiments dashboard

import requests
import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_auth import (
    assert_response_ok,
    auth_headers,
    get_gateway_api_url,
    require_auth,
)

GATEWAY_API_URL = get_gateway_api_url()
require_auth()


st.title("ML Experiments")

# Fetch experiments (admin only)
try:
    exp_response = requests.get(
        f"{GATEWAY_API_URL}/experiments/",
        headers=auth_headers(),
    )
    assert_response_ok(exp_response, admin_only=True)
    experiments = exp_response.json()
except Exception as e:
    st.error(f"Cannot reach gateway: {e}")
    st.stop()

if not experiments:
    st.warning("No experiments found")
    st.stop()

# Fetch current production model (user + admin)
prod_model = None
try:
    prod_response = requests.get(
        f"{GATEWAY_API_URL}/models/current",
        headers=auth_headers(),
    )
    if prod_response.status_code == 200:
        prod_model = prod_response.json()
    elif prod_response.status_code in (401, 403):
        assert_response_ok(prod_response)
except Exception:
    st.warning("Could not fetch production model")

if prod_model:
    st.success(
        f"""
        Production Model  
        Version: {prod_model['registered_model_version']}  
        Run ID: {prod_model['run_id']}
        """
    )
else:
    st.info("No production model found")

st.divider()

experiment_map = {
    e["name"]: e["experiment_id"] for e in experiments
}

selected_exp_name = st.selectbox(
    "Select experiment",
    list(experiment_map.keys())
)

experiment_id = experiment_map[selected_exp_name]

# Fetch runs
runs_response = requests.get(
    f"{GATEWAY_API_URL}/experiments/{experiment_id}/runs",
    headers=auth_headers(),
)
assert_response_ok(runs_response, admin_only=True)

runs = runs_response.json()

if not runs:
    st.warning("No runs found")
    st.stop()

df = pd.DataFrame(runs)

# Flatten metrics
if "metrics" in df.columns:
    metrics_df = df["metrics"].apply(pd.Series)
    df = pd.concat([df.drop(columns=["metrics"]), metrics_df], axis=1)

# Sort by RMSLE
if "reference_rmsle" in df.columns:
    df = df.sort_values("reference_rmsle")

# Add production flag
if prod_model:
    df["production"] = df["run_id"] == prod_model["run_id"]
else:
    df["production"] = False

st.subheader("Runs")
st.dataframe(df, use_container_width=True)

# RMSLE interactive graph
if "reference_rmsle" in df.columns:

    st.subheader("RMSLE Comparison")

    fig = px.scatter(
        df,
        x="run_id",
        y="reference_rmsle",
        color="production",
        hover_data=df.columns,
        title="RMSLE per Run",
    )

    st.plotly_chart(fig, use_container_width=True)

st.divider()

# Promote section
st.subheader("Promote Model")

selected_run = st.selectbox(
    "Select run to promote",
    df["run_id"]
)

if st.button("Promote to Production"):

    response = requests.post(
        f"{GATEWAY_API_URL}/models/promote",
        params={"run_id": selected_run},
        headers=auth_headers(),
    )

    if response.status_code == 200:
        st.success("Model promoted successfully")
        st.rerun()
    else:
        if response.status_code in (401, 403):
            assert_response_ok(response, admin_only=True)
        st.error(response.text or "Promotion failed")

# Refresh
if st.button("Refresh"):
    st.rerun()
