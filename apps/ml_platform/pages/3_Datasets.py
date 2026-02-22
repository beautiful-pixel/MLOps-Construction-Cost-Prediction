# Data & Retrain Policy Control Tower

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

DATA_DAG = "data_pipeline_dag"
POLICY_DAG = "retrain_policy_dag"

st.title("Data & Retrain Policy Control Tower")

# Auto refresh
auto_refresh = st.checkbox("Auto refresh (5s)", value=False)

# Dataset overview
st.subheader("Dataset Overview")

overview_response = requests.get(
    f"{GATEWAY_API_URL}/datasets/overview",
    headers=auth_headers(),
)
assert_response_ok(overview_response, admin_only=True)

overview = overview_response.json()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Master rows", overview["master_rows"])
col2.metric("New rows", overview["new_rows"])
col3.metric("Threshold", overview["threshold"])
col4.metric(
    "Retrain required",
    "YES" if overview["should_retrain"] else "NO"
)

new_threshold = st.number_input(
    "Edit retrain threshold (rows)",
    min_value=1,
    value=overview["threshold"],
)

if st.button("Update Threshold"):
    r = requests.post(
        f"{GATEWAY_API_URL}/datasets/threshold",
        params={"threshold": int(new_threshold)},
        headers=auth_headers(),
    )
    assert_response_ok(r, admin_only=True)
    st.success("Threshold updated")
    st.rerun()

st.divider()

# Global orchestration
st.subheader("Global Orchestration")

global_dot = graphviz.Digraph()
global_dot.attr(rankdir="LR")
global_dot.attr("node", shape="box", style="filled")

global_dot.node("data", "Data Pipeline", fillcolor="#63b3ed")
global_dot.node("policy", "Retrain Policy", fillcolor="#f6ad55")
global_dot.node("train", "Train Pipeline", fillcolor="#68d391")

global_dot.edge("data", "policy")
global_dot.edge("policy", "train")

st.graphviz_chart(global_dot, use_container_width=True)

st.divider()

status_color = {
    "success": "#48bb78",
    "failed": "#f56565",
    "running": "#ecc94b",
    "queued": "#a0aec0",
    "skipped": "#63b3ed",
    None: "#a0aec0",
}

# Render DAG
def render_dag(dag_id, title):

    st.subheader(title)

    runs_response = requests.get(
        f"{GATEWAY_API_URL}/pipeline/dags/{dag_id}/runs",
        headers=auth_headers(),
    )
    assert_response_ok(runs_response, admin_only=True)

    runs = runs_response.json().get("dag_runs", [])

    if not runs:
        st.info("No runs found")
        return

    df_runs = pd.DataFrame(runs)
    df_runs = df_runs.sort_values("start_date", ascending=False)

    selected_run = st.selectbox(
        f"Select run ({dag_id})",
        df_runs["dag_run_id"],
        key=dag_id,
    )

    tasks_response = requests.get(
        f"{GATEWAY_API_URL}/pipeline/dags/{dag_id}/runs/{selected_run}/tasks",
        headers=auth_headers(),
    )
    assert_response_ok(tasks_response, admin_only=True)

    tasks = tasks_response.json().get("task_instances", [])

    if not tasks:
        st.warning("No task instances found")
        return

    df_tasks = pd.DataFrame(tasks)

    total_tasks = len(df_tasks)
    finished_tasks = len(
        df_tasks[df_tasks["state"].isin(["success", "failed", "skipped"])]
    )

    progress = finished_tasks / total_tasks if total_tasks else 0
    st.progress(progress)

    dot = graphviz.Digraph()
    dot.attr(rankdir="LR")
    dot.attr("node", shape="box", style="filled")

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

# Data pipeline DAG
render_dag(DATA_DAG, "Data Pipeline DAG")

st.divider()

# Retrain policy DAG
render_dag(POLICY_DAG, "Retrain Policy DAG")

# Auto refresh
if auto_refresh:
    time.sleep(5)
    st.rerun()