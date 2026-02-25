# Train Control Tower

import requests
import streamlit as st
import pandas as pd
import time
import graphviz

from streamlit_auth import (
    assert_response_ok,
    auth_headers,
    get_gateway_api_url,
    require_auth,
)

GATEWAY_API_URL = get_gateway_api_url()
require_auth()


# --- Airflow-like UI palette ---
AIRFLOW_BRAND_BLUE = "#017CEE"
AIRFLOW_STATE_COLOR = {
        "success": "#22c55e",  # green-500
        "failed": "#ef4444",  # red-500
        "running": "#06b6d4",  # cyan-500
        "queued": "#a8a29e",  # stone-400
        "scheduled": "#a1a1aa",  # zinc-400
        "skipped": "#f472b6",  # pink-400
        "upstream_failed": "#f97316",  # orange-500
        "up_for_retry": "#facc15",  # yellow-400
        None: "#9ca3af",  # gray-400
}

st.markdown(
        f"""
<style>
    div.stButton > button {{
        background-color: {AIRFLOW_BRAND_BLUE};
        border-color: {AIRFLOW_BRAND_BLUE};
        color: white;
    }}
    div.stButton > button:hover {{
        filter: brightness(0.95);
        border-color: {AIRFLOW_BRAND_BLUE};
    }}
    div.stButton > button:focus:not(:active) {{
        box-shadow: 0 0 0 0.2rem rgba(1, 124, 238, 0.25);
    }}
</style>
""",
        unsafe_allow_html=True,
)

DAG_ID = "train_pipeline_dag"

st.title("Train Control Tower")

# Auto refresh
auto_refresh = st.checkbox("Auto refresh (5s)", value=False)

# Trigger section
st.subheader("Trigger Training")

conf = {}

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

if st.button("Trigger Training"):
    response = requests.post(
        f"{GATEWAY_API_URL}/pipeline/trigger",
        json={
            "dag_id": DAG_ID,
            "conf": conf,
        },
        headers=auth_headers(),
    )

    if response.status_code == 200:
        st.success("Training triggered successfully")
        st.rerun()
    else:
        assert_response_ok(response, admin_only=True)
        st.error(response.text)

st.divider()

# Fetch DAG runs
runs_response = requests.get(
    f"{GATEWAY_API_URL}/pipeline/dags/{DAG_ID}/runs",
    headers=auth_headers(),
)
assert_response_ok(runs_response, admin_only=True)

runs = runs_response.json().get("dag_runs", [])

if not runs:
    st.info("No training runs found")
    st.stop()

df_runs = pd.DataFrame(runs)
df_runs = df_runs.sort_values("start_date", ascending=False)

selected_run = st.selectbox(
    "Select training run",
    df_runs["dag_run_id"]
)

# Fetch tasks
tasks_response = requests.get(
    f"{GATEWAY_API_URL}/pipeline/dags/{DAG_ID}/runs/{selected_run}/tasks",
    headers=auth_headers(),
)
assert_response_ok(tasks_response, admin_only=True)

tasks = tasks_response.json().get("task_instances", [])

if not tasks:
    st.warning("No task instances found")
    st.stop()

df_tasks = pd.DataFrame(tasks)

# KPIs
total_tasks = len(df_tasks)
success_tasks = len(df_tasks[df_tasks["state"] == "success"])
running_tasks = len(df_tasks[df_tasks["state"] == "running"])
failed_tasks = len(df_tasks[df_tasks["state"] == "failed"])

finished_tasks = len(
    df_tasks[df_tasks["state"].isin(["success", "failed"])]
)

progress = finished_tasks / total_tasks if total_tasks else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total", total_tasks)
col2.metric("Success", success_tasks)
col3.metric("Running", running_tasks)
col4.metric("Failed", failed_tasks)

st.progress(progress)

# DAG Visualization
st.subheader("Training DAG View")

status_color = {
    "success": AIRFLOW_STATE_COLOR["success"],
    "failed": AIRFLOW_STATE_COLOR["failed"],
    "running": AIRFLOW_STATE_COLOR["running"],
    "queued": AIRFLOW_STATE_COLOR["queued"],
    "scheduled": AIRFLOW_STATE_COLOR["scheduled"],
    "skipped": AIRFLOW_STATE_COLOR["skipped"],
    "upstream_failed": AIRFLOW_STATE_COLOR["upstream_failed"],
    "up_for_retry": AIRFLOW_STATE_COLOR["up_for_retry"],
    None: AIRFLOW_STATE_COLOR[None],
}

dot = graphviz.Digraph()
dot.attr(rankdir="LR")
dot.attr("node", shape="box", style="filled", fontname="Helvetica")

# Sort by start_date for visual coherence (linear DAG assumption)
df_tasks_sorted = df_tasks.sort_values("start_date")

previous_task = None

for _, row in df_tasks_sorted.iterrows():
    task_id = row["task_id"]
    state = row["state"]

    color = status_color.get(state, "#a0aec0")

    penwidth = "3" if state == "running" else "1"
    fontcolor = "white" if state == "failed" else "black"

    dot.node(
        task_id,
        label=f"{task_id}\n{state}",
        fillcolor=color,
        fontcolor=fontcolor,
        penwidth=penwidth,
    )

    if previous_task:
        dot.edge(previous_task, task_id)

    previous_task = task_id

st.graphviz_chart(dot, use_container_width=True)

# Auto refresh
if auto_refresh:
    time.sleep(5)
    st.rerun()