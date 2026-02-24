from __future__ import annotations

import os
import streamlit as st
import streamlit.components.v1 as components
from streamlit_auth import login_sidebar


GRAFANA_DASHBOARD_URL = os.getenv("GRAFANA_DASHBOARD_URL")
GRAFANA_ALERTS_URL = os.getenv("GRAFANA_ALERTS_URL")
GRAFANA_PUBLIC_URL = os.getenv("GRAFANA_PUBLIC_URL")
GRAFANA_PORT = os.getenv("GRAFANA_PORT")

login_sidebar()

st.title("Monitoring")


def render_grafana(path: str, height: int, explicit_url: str | None) -> None:
    if explicit_url:
        components.iframe(explicit_url, height=height)
        return

    if GRAFANA_PUBLIC_URL:
        base = GRAFANA_PUBLIC_URL.rstrip("/")
        if not path.startswith("/"):
            path = f"/{path}"
        components.iframe(f"{base}{path}", height=height)
        return

    if not GRAFANA_PORT:
        st.error(
            "Set GRAFANA_PUBLIC_URL or GRAFANA_PORT to render Grafana."
        )
        st.stop()

    try:
        port = int(GRAFANA_PORT)
    except ValueError:
        st.error("GRAFANA_PORT must be numeric.")
        st.stop()

    if not path.startswith("/"):
        path = f"/{path}"

    html = f"""
    <script>
    (function() {{
        let parentLocation = window.location;
        try {{
            if (window.parent && window.parent.location) {{
                parentLocation = window.parent.location;
            }}
        }} catch (err) {{
            parentLocation = window.location;
        }}
        const base = parentLocation.protocol + '//' + parentLocation.hostname + ':{port}';
        const url = base + {path!r};
        const iframe = document.createElement('iframe');
        iframe.src = url;
        iframe.style.width = '100%';
        iframe.style.height = '{height}px';
        iframe.style.border = '0';
        document.body.appendChild(iframe);
    }})();
    </script>
    """
    components.html(html, height=height + 20)


st.subheader("Grafana Overview")
render_grafana("/dashboards", 800, GRAFANA_DASHBOARD_URL)

st.subheader("Grafana Alerting")
render_grafana("/alerting/list", 700, GRAFANA_ALERTS_URL)
