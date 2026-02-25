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


# Fetch experiments

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


# Fetch production model

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
        f"Production Model | Version: {prod_model['registered_model_version']} | Run ID: {prod_model['run_id']}"
    )
else:
    st.info("No production model found")

st.divider()


# Select experiment

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


# Flatten nested fields

if "metrics" in df.columns:
    metrics_df = df["metrics"].apply(pd.Series)
    df = pd.concat([df.drop(columns=["metrics"]), metrics_df], axis=1)

if "params" in df.columns:
    params_df = df["params"].apply(pd.Series)
    df = pd.concat([df.drop(columns=["params"]), params_df], axis=1)

if "tags" in df.columns:
    tags_df = df["tags"].apply(pd.Series)
    df = pd.concat([df.drop(columns=["tags"]), tags_df], axis=1)

# Convert timestamps if available
if "start_time" in df.columns:
    df["start_time"] = pd.to_datetime(df["start_time"], unit="ms")

if "end_time" in df.columns:
    df["end_time"] = pd.to_datetime(df["end_time"], unit="ms")


# Keep only finished runs
if "status" in df.columns:
    df = df[df["status"] == "FINISHED"]


# Production flag
if prod_model:
    df["production"] = df["run_id"] == prod_model["run_id"]
else:
    df["production"] = False


# Metric selection

metric_columns = [
    col for col in df.columns
    if col.startswith("reference_")
    and pd.api.types.is_numeric_dtype(df[col])
]

if not metric_columns:
    st.warning("No reference metrics available")
    st.stop()

selected_metric = st.selectbox(
    "Select metric",
    metric_columns,
    index=metric_columns.index("reference_rmsle")
    if "reference_rmsle" in metric_columns
    else 0,
)

higher_is_better = "r2" in selected_metric.lower()

df = df.sort_values(
    selected_metric,
    ascending=not higher_is_better
)

best_run_id = df.iloc[0]["run_id"]
df["best"] = df["run_id"] == best_run_id


# KPI header

col1, col2, col3 = st.columns(3)

col1.metric("Total Runs", len(df))

best_value = df.iloc[0][selected_metric]
col2.metric("Best", round(best_value, 4))

if prod_model:
    prod_row = df[df["production"]]
    if not prod_row.empty:
        prod_value = prod_row.iloc[0][selected_metric]
        delta = prod_value - best_value if higher_is_better else best_value - prod_value
        col3.metric("Production", round(prod_value, 4), delta=round(delta, 4))


st.divider()


# Runs table

st.subheader("Runs")

st.dataframe(df, use_container_width=True)


# Metric chart

st.subheader("Metric Comparison")

x_axis = "start_time" if "start_time" in df.columns else "run_id"

fig = px.scatter(
    df,
    x=x_axis,
    y=selected_metric,
    color="production",
    symbol="best",
    hover_data=df.columns,
    title=f"{selected_metric} per Run",
)

st.plotly_chart(fig, use_container_width=True)


# Multi-metric comparison

st.subheader("Multi-Metric Comparison")

selected_metrics = st.multiselect(
    "Select metrics to compare",
    metric_columns,
    default=metric_columns,
)

if selected_metrics:
    fig_multi = px.line(
        df,
        x=x_axis,
        y=selected_metrics,
        markers=True,
        title="Metrics Comparison",
    )
    st.plotly_chart(fig_multi, use_container_width=True)


st.divider()


# Promote section

st.subheader("Promote Model")

selected_run = st.selectbox(
    "Select run to promote",
    df["run_id"]
)

selected_row = df[df["run_id"] == selected_run].iloc[0]
st.json(selected_row.to_dict())

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

# reload inference API after promotion

st.subheader("Serving Controls")
st.caption("reload the model served by the inference API after a promotion.")

if st.button("Reload production model (Inference API)"):
    with st.spinner("Reloading model..."):
        r = requests.post(
            f"{GATEWAY_API_URL}/reload",
            headers=auth_headers(),
            timeout=20,
        )
    assert_response_ok(r, admin_only=True)
    payload = r.json()
    st.success(
        "Reload OK — "
        f"model_version={payload.get('model_version')} | "
        f"run_id={payload.get('run_id')}"
    )

st.divider()

# Refresh

if st.button("Refresh"):
    st.rerun()