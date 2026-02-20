# Pipeline control tower

import requests
import streamlit as st
import pandas as pd
import time
from streamlit_auth import (
    assert_response_ok,
    auth_headers,
    get_gateway_api_url,
    require_auth,
)

GATEWAY_API_URL = get_gateway_api_url()
require_auth()

st.title("Pipeline Control Tower")

# Auto refresh toggle
auto_refresh = st.checkbox("Auto refresh (5s)", value=False)

# Select DAG
dag_options = [
    "data_pipeline_dag",
    "train_pipeline_dag",
]

selected_dag = st.selectbox("Select DAG", dag_options)

# Trigger section
st.subheader("Trigger Pipeline")

conf = {}

if selected_dag == "train_pipeline_dag":

    # Load feature schema metadata
    try:
        r = requests.get(
            f"{GATEWAY_API_URL}/configs/feature-schemas",
            headers=auth_headers(),
        )
        assert_response_ok(r, admin_only=True)
        feature_meta = r.json()

        available_features = feature_meta["available_feature_versions"]
        default_feature = feature_meta["default_feature_version"]
        contract_version = feature_meta["data_contract"]

    except Exception as e:
        st.error(f"Unable to load feature schemas: {e}")
        st.stop()

    st.info(f"Active Data Contract: v{contract_version}")

    if not available_features:
        st.warning("No feature schema versions available.")
        st.stop()

    feature_version = st.selectbox(
        "Feature schema version",
        available_features,
        index=available_features.index(default_feature)
        if default_feature in available_features else 0
    )

    # Load model schema metadata
    try:
        r = requests.get(
            f"{GATEWAY_API_URL}/configs/model-schemas",
            headers=auth_headers(),
        )
        assert_response_ok(r, admin_only=True)
        model_meta = r.json()

        available_models = model_meta["available_model_versions"]
        default_model = model_meta["default_model_version"]

    except Exception as e:
        st.error(f"Unable to load model schemas: {e}")
        st.stop()

    if not available_models:
        st.warning("No model schema versions available.")
        st.stop()

    model_version = st.selectbox(
        "Model schema version",
        available_models,
        index=available_models.index(default_model)
        if default_model in available_models else 0
    )

    split_version = st.number_input(
        "Split version",
        min_value=1,
        step=1,
        value=1,
    )

    conf = {
        "feature_version": int(feature_version),
        "model_version": int(model_version),
        "split_version": int(split_version),
    }


if st.button("Trigger DAG"):

    response = requests.post(
        f"{GATEWAY_API_URL}/pipeline/trigger",
        json={
            "dag_id": selected_dag,
            "conf": conf,
        },
        headers=auth_headers(),
    )

    if response.status_code == 200:
        st.success("DAG triggered successfully")
        st.rerun()
    else:
        if response.status_code in (401, 403):
            assert_response_ok(response, admin_only=True)
        st.error(response.text)

st.divider()

# Fetch DAG runs
runs_response = requests.get(
    f"{GATEWAY_API_URL}/pipeline/dags/{selected_dag}/runs",
    headers=auth_headers(),
)
assert_response_ok(runs_response, admin_only=True)

runs_data = runs_response.json()
runs = runs_data.get("dag_runs", [])

if not runs:
    st.info("No runs found")
    st.stop()

df_runs = pd.DataFrame(runs)

# Sort newest first
df_runs = df_runs.sort_values("start_date", ascending=False)

st.subheader("DAG Runs")

# Status color mapping
def color_status(val):
    if val == "success":
        return "background-color: #c6f6d5"
    if val == "failed":
        return "background-color: #fed7d7"
    if val == "running":
        return "background-color: #fefcbf"
    return ""

styled_df = df_runs.style.applymap(color_status, subset=["state"])

st.dataframe(styled_df, use_container_width=True)

selected_run = st.selectbox(
    "Select run",
    df_runs["dag_run_id"]
)

# Fetch tasks
tasks_response = requests.get(
    f"{GATEWAY_API_URL}/pipeline/dags/{selected_dag}/runs/{selected_run}/tasks",
    headers=auth_headers(),
)
assert_response_ok(tasks_response, admin_only=True)

tasks_data = tasks_response.json()
tasks = tasks_data.get("task_instances", [])

if tasks:

    df_tasks = pd.DataFrame(tasks)

    st.subheader("Task Instances")

    total_tasks = len(df_tasks)
    finished_tasks = len(
        df_tasks[df_tasks["state"].isin(["success", "failed"])]
    )

    progress = finished_tasks / total_tasks if total_tasks else 0
    st.progress(progress)

    styled_tasks = df_tasks.style.applymap(
        color_status,
        subset=["state"]
    )

    st.dataframe(styled_tasks, use_container_width=True)

# Auto refresh
if auto_refresh:
    time.sleep(5)
    st.rerun()
