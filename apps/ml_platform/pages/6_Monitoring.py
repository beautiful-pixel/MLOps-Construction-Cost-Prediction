import os
import streamlit as st
import streamlit.components.v1 as components


GRAFANA_URL = os.getenv("GRAFANA_URL")
GRAFANA_DASHBOARD_URL = os.getenv("GRAFANA_DASHBOARD_URL")
GRAFANA_ALERTS_URL = os.getenv("GRAFANA_ALERTS_URL")

st.title("Monitoring")

if not GRAFANA_URL:
    st.error("GRAFANA_URL is not set.")
    st.stop()

overview_url = GRAFANA_DASHBOARD_URL or f"{GRAFANA_URL}/dashboards"
alerts_url = GRAFANA_ALERTS_URL or f"{GRAFANA_URL}/alerting/list"

st.subheader("Grafana Overview")
components.iframe(overview_url, height=800)

st.subheader("Grafana Alerting")
components.iframe(alerts_url, height=700)
