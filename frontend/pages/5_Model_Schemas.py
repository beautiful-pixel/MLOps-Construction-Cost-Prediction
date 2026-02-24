# Admin - Model Schema Management

import requests
import streamlit as st
from streamlit_auth import (
    assert_response_ok,
    auth_headers,
    get_gateway_api_url,
    require_auth,
)

GATEWAY_API_URL = get_gateway_api_url()
require_auth()

st.title("Model Schema Admin")


# Load metadata

try:
    r = requests.get(
        f"{GATEWAY_API_URL}/configs/model-schemas",
        headers=auth_headers(),
    )
    assert_response_ok(r, admin_only=True)
    model_meta = r.json()
    available_model_versions = model_meta.get("available_model_versions", [])
    default_model_version = model_meta.get("default_model_version")
except Exception:
    st.error("Unable to load model metadata")
    st.stop()


try:
    r = requests.get(
        f"{GATEWAY_API_URL}/configs/model-schemas/supported",
        headers=auth_headers(),
    )
    assert_response_ok(r, admin_only=True)
    supported_models = r.json()
except Exception:
    st.error("Unable to load supported model definitions")
    st.stop()


if not available_model_versions:
    st.warning("No model versions available")
    st.stop()


# Version selector

selected_model_version = st.selectbox(
    "Select Model Schema Version",
    options=available_model_versions,
    index=available_model_versions.index(default_model_version)
    if default_model_version in available_model_versions
    else 0,
)

try:
    r = requests.get(
        f"{GATEWAY_API_URL}/configs/model-schemas/{selected_model_version}",
        headers=auth_headers(),
    )
    assert_response_ok(r, admin_only=True)
    selected_schema = r.json()
    schema_model_type = selected_schema["model"]["type"]
    schema_params = selected_schema["model"]["params"]
except Exception:
    st.error("Unable to load selected model schema")
    st.stop()


st.info(f"Default Model Version: {default_model_version}")
st.info(f"Selected Model Type: {schema_model_type}")

st.divider()


# Session state

if "model_builder" not in st.session_state:
    st.session_state.model_builder = {}

if "model_type_builder" not in st.session_state:
    st.session_state.model_type_builder = None

if "edit_mode_model" not in st.session_state:
    st.session_state.edit_mode_model = False


# Load selected version for editing

if st.button("Load Selected Version for Editing"):
    st.session_state.model_builder = schema_params.copy()
    st.session_state.model_type_builder = schema_model_type
    st.session_state.edit_mode_model = True
    st.success("Model schema loaded into editor")
    st.rerun()


st.divider()
st.subheader("Add / Modify Model Parameters")


# MODE EDITION → type locked
if st.session_state.edit_mode_model:
    selected_model_type = st.session_state.model_type_builder
    st.write(f"Editing Model Type: **{selected_model_type}**")

# MODE CREATION → type selectable
else:
    selected_model_type = st.selectbox(
        "Select Model Type",
        options=list(supported_models.keys()),
    )
    st.session_state.model_type_builder = selected_model_type


supported_params = supported_models[selected_model_type]["parameters"]
configured_params = set(st.session_state.model_builder.keys())


# Select parameter to edit/add

def format_param_label(p):
    if p in configured_params:
        return f"✔ {p}"
    return p


selected_param = st.selectbox(
    "Select parameter",
    options=list(supported_params.keys()),
    format_func=format_param_label,
)


param_meta = supported_params[selected_param]
param_type = param_meta["type"]
default_value = param_meta["default"]

existing_value = st.session_state.model_builder.get(
    selected_param,
    default_value,
)


# Parameter input

if param_type == "int":
    value = st.number_input(
        "Value",
        value=int(existing_value),
        step=1,
    )

elif param_type == "float":
    value = st.number_input(
        "Value",
        value=float(existing_value),
        format="%.6f",
    )

elif param_type == "bool":
    value = st.checkbox(
        "Value",
        value=bool(existing_value),
    )

else:
    value = st.text_input(
        "Value",
        value=str(existing_value),
    )


# Add / Update parameter

if st.button("Add / Update Parameter"):
    st.session_state.model_builder[selected_param] = value
    st.success(f"{selected_param} added/updated")
    st.rerun()


# Delete parameter

if selected_param in st.session_state.model_builder:
    if st.button("Delete Parameter"):
        del st.session_state.model_builder[selected_param]
        st.success(f"{selected_param} removed")
        st.rerun()


# Working schema preview

st.divider()
st.subheader("Working Model Schema")

if st.session_state.model_builder:
    st.json({
        "type": st.session_state.model_type_builder,
        "params": st.session_state.model_builder,
    })
else:
    st.info("No parameters configured yet.")


# Reset

if st.button("Reset Editor"):
    st.session_state.model_builder = {}
    st.session_state.model_type_builder = None
    st.session_state.edit_mode_model = False
    st.rerun()


# Create new version

if st.button("Create New Model Version"):

    if not st.session_state.model_builder:
        st.warning("No parameters defined")
        st.stop()

    payload = {
        "type": st.session_state.model_type_builder,
        "params": st.session_state.model_builder,
    }

    r = requests.post(
        f"{GATEWAY_API_URL}/configs/model-schemas",
        json=payload,
        headers=auth_headers(),
    )

    if r.status_code == 200:
        version = r.json()["model_schema_version"]
        st.success(f"Model version {version} created")
        st.session_state.model_builder = {}
        st.session_state.model_type_builder = None
        st.session_state.edit_mode_model = False
        st.rerun()
    else:
        if r.status_code in (401, 403):
            assert_response_ok(r, admin_only=True)
        st.error(r.text)


# Set default version

st.divider()

if st.button("Set Selected Version as Default"):

    r = requests.post(
        f"{GATEWAY_API_URL}/configs/model-schemas/default",
        params={"version": selected_model_version},
        headers=auth_headers(),
    )

    if r.status_code == 200:
        st.success("Default model version updated")
        st.rerun()
    else:
        if r.status_code in (401, 403):
            assert_response_ok(r, admin_only=True)
        st.error(r.text)