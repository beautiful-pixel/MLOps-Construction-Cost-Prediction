# Data & Retrain Policy Control Tower

import requests
import streamlit as st
import pandas as pd
import time
import graphviz
import os
import datetime as dt
import matplotlib.pyplot as plt

from streamlit_auth import (
    assert_response_ok,
    auth_headers,
    get_gateway_api_url,
    require_auth,
)

GATEWAY_API_URL = get_gateway_api_url()
require_auth()


# --- Airflow-like UI palette ---
# Airflow UI uses a Tailwind-based semantic palette (success/failed/running/etc)
# and a brand blue. We reuse a close equivalent here for visual consistency.
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

DATA_DAG = "data_pipeline_dag"
POLICY_DAG = "retrain_policy_dag"

st.title("Data & Retrain Policy Control Tower")

# Auto refresh
auto_refresh = st.checkbox("Auto refresh (5s)", value=False)


def _get_prometheus_url() -> str:
    return os.getenv("PROMETHEUS_URL", "http://prometheus:9090")


def _prom_query_range(query: str, start: dt.datetime, end: dt.datetime, step_seconds: int):
    url = f"{_get_prometheus_url()}/api/v1/query_range"
    r = requests.get(
        url,
        params={
            "query": query,
            "start": start.timestamp(),
            "end": end.timestamp(),
            "step": step_seconds,
        },
        timeout=5,
    )
    r.raise_for_status()
    payload = r.json()
    if payload.get("status") != "success":
        raise RuntimeError(f"Prometheus query failed: {payload}")
    return payload.get("data", {}).get("result", [])


st.subheader("Dataset Volumetry")

days = st.slider("History (days)", min_value=3, max_value=14, value=7)
end = dt.datetime.now(dt.timezone.utc)
start = end - dt.timedelta(days=int(days))

try:
    result = _prom_query_range(
        query="mlops_dataset_master_rows",
        start=start,
        end=end,
        step_seconds=60 * 60 * 6,  # 6h
    )

    if not result:
        st.info("No Prometheus time-series yet. Wait a few scrapes, then refresh.")
    else:
        values = result[0].get("values", [])
        if not values:
            st.info("No Prometheus samples yet. Wait a bit, then refresh.")
        else:
            ts = [dt.datetime.fromtimestamp(float(t), tz=dt.timezone.utc) for t, _ in values]
            ys = [float(v) for _, v in values]
            df_vol = pd.DataFrame({"timestamp": ts, "master_rows": ys}).set_index("timestamp")

            # Daily snapshot + delta/day
            daily = df_vol["master_rows"].resample("1D").last().dropna()
            daily_delta = daily.diff().dropna()

            fig, axes = plt.subplots(2, 1, figsize=(6, 4), constrained_layout=True)

            axes[0].plot(
                df_vol.index,
                df_vol["master_rows"],
                linewidth=2,
                color=AIRFLOW_BRAND_BLUE,
            )
            axes[0].set_title("Master rows over time")
            axes[0].set_ylabel("rows")
            axes[0].grid(True, alpha=0.3)

            if not daily_delta.empty:
                axes[1].bar(
                    daily_delta.index,
                    daily_delta.values,
                    color=AIRFLOW_STATE_COLOR["running"],
                )
                axes[1].set_title("Delta per day")
                axes[1].set_ylabel("rows/day")
                axes[1].grid(True, axis="y", alpha=0.3)
            else:
                axes[1].text(0.5, 0.5, "Not enough history for daily delta", ha="center", va="center")
                axes[1].set_axis_off()

            st.pyplot(fig, clear_figure=True)

except Exception as exc:
    st.warning(f"Volumetry unavailable (Prometheus): {exc}")

# Retrain policy
st.subheader("Retrain Policy")

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
global_dot.attr("edge", fontsize="16", fontcolor="#334155")
global_dot.attr(
    "node",
    shape="box",
    style="rounded,filled",
    fillcolor="#f8fafc",
    color=AIRFLOW_BRAND_BLUE,
    fontcolor="#0f172a",
    fontsize="22",
    margin="0.25,0.18",
)

global_dot.node("data", "Data Pipeline")
global_dot.node("policy", "Retrain Policy")
global_dot.node("train", "Train Pipeline")

global_dot.edge(
    "data",
    "policy",
    label="Triggers when preprocessing is needed\n(_READY present)",
)
global_dot.edge(
    "policy",
    "train",
    label=f"Triggers when new rows exceed threshold\n(new_rows > {overview['threshold']})",
)

st.graphviz_chart(global_dot.source, use_container_width=True)

st.divider()

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


def render_state_legend() -> None:
    # Small legend for Airflow task-state colors.
    chips = [
        ("Success", status_color["success"]),
        ("Running", status_color["running"]),
        ("Queued", status_color["queued"]),
        ("Skipped", status_color["skipped"]),
        ("Upstream failed", status_color["upstream_failed"]),
        ("Failed", status_color["failed"]),
        ("Up for retry", status_color["up_for_retry"]),
    ]

    html = "".join(
        [
            f"""
<span style="display:inline-flex; align-items:center; gap:6px; margin-right:12px;">
  <span style="display:inline-block; width:10px; height:10px; border-radius:2px; background:{color}; border:1px solid rgba(0,0,0,0.08);"></span>
  <span style="font-size:12px; color:#334155;">{label}</span>
</span>
"""
            for label, color in chips
        ]
    )
    st.markdown(html, unsafe_allow_html=True)

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


def render_dag_one_line(dag_id: str, title: str) -> None:
    """Render a *linear* DAG on a single horizontal line."""

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

    df_runs = pd.DataFrame(runs).sort_values("start_date", ascending=False)
    selected_run = st.selectbox(
        f"Select run ({dag_id})",
        df_runs["dag_run_id"],
        key=f"{dag_id}__one_line",
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
    finished_tasks = len(df_tasks[df_tasks["state"].isin(["success", "failed", "skipped"])])
    progress = finished_tasks / total_tasks if total_tasks else 0
    st.progress(progress)

    df_tasks_sorted = df_tasks.sort_values("start_date")

    dot = graphviz.Digraph()
    dot.attr(rankdir="LR")
    dot.attr("graph", nodesep="0.25", ranksep="0.45", splines="polyline")
    dot.attr("edge", arrowsize="0.7")
    dot.attr(
        "node",
        shape="box",
        style="filled",
        fontname="Helvetica",
        fontsize="14",
        margin="0.25,0.18",
    )

    previous_task = None

    for _, row in df_tasks_sorted.iterrows():
        task_id = str(row["task_id"])
        state = row["state"]

        color = status_color.get(state, AIRFLOW_STATE_COLOR[None])

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

    st.graphviz_chart(dot.source, use_container_width=True)


def render_dag_two_rows(dag_id: str, title: str) -> None:
    """Render a *linear* DAG wrapped into 2 horizontal rows for readability."""

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

    df_runs = pd.DataFrame(runs).sort_values("start_date", ascending=False)
    selected_run = st.selectbox(
        f"Select run ({dag_id})",
        df_runs["dag_run_id"],
        key=f"{dag_id}__two_rows",
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
    finished_tasks = len(df_tasks[df_tasks["state"].isin(["success", "failed", "skipped"])])
    progress = finished_tasks / total_tasks if total_tasks else 0
    st.progress(progress)

    df_tasks_sorted = df_tasks.sort_values("start_date")
    ordered_task_ids = [str(t) for t in df_tasks_sorted["task_id"].tolist()]

    split_idx = (len(ordered_task_ids) + 1) // 2
    row1 = ordered_task_ids[:split_idx]
    row2 = ordered_task_ids[split_idx:]

    dot = graphviz.Digraph()
    dot.attr(rankdir="TB")
    dot.attr(
        "node",
        shape="box",
        style="filled",
        fontname="Helvetica",
        fontsize="12",
        margin="0.25,0.18",
        width="2.8",
        height="0.9",
        fixedsize="true",
    )

    # Nodes
    for _, row in df_tasks_sorted.iterrows():
        task_id = str(row["task_id"])
        state = row["state"]
        color = status_color.get(state, AIRFLOW_STATE_COLOR[None])
        penwidth = "3" if state == "running" else "1"
        fontcolor = "white" if state == "failed" else "black"
        dot.node(
            task_id,
            label=f"{task_id}\n{state}",
            fillcolor=color,
            fontcolor=fontcolor,
            penwidth=penwidth,
        )

    # Rank groups (2 rows)
    if row1:
        with dot.subgraph(name="cluster_row1") as s:
            s.attr(rank="same")
            for task_id in row1:
                s.node(task_id)
            for a, b in zip(row1, row1[1:]):
                s.edge(a, b, style="invis", weight="10")

    if row2:
        with dot.subgraph(name="cluster_row2") as s:
            s.attr(rank="same")
            for task_id in row2:
                s.node(task_id)
            for a, b in zip(row2, row2[1:]):
                s.edge(a, b, style="invis", weight="10")

    # Visible edges: row1 chain, wrap edge, row2 chain.
    for a, b in zip(row1, row1[1:]):
        dot.edge(a, b, constraint="false")
    if row1 and row2:
        dot.edge(row1[-1], row2[0])
    for a, b in zip(row2, row2[1:]):
        dot.edge(a, b, constraint="false")

    st.graphviz_chart(dot, use_container_width=True)

# Data pipeline DAG
st.caption("Task state colors")
render_state_legend()
render_dag_one_line(DATA_DAG, "Data Pipeline DAG")

st.divider()

# Retrain policy DAG
render_dag(POLICY_DAG, "Retrain Policy DAG")

# Auto refresh
if auto_refresh:
    time.sleep(5)
    st.rerun()