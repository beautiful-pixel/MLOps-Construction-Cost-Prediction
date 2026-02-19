# Admin - Model Schema Management

import os
import requests
import streamlit as st

GATEWAY_API_URL = os.environ["GATEWAY_API_URL"]

st.title("Model Schema Admin")


# Load model versions metadata

try:
    r = requests.get(f"{GATEWAY_API_URL}/configs/model-schemas")
    model_meta = r.json()
    available_model_versions = model_meta.get("available_model_versions", [])
    default_model_version = model_meta.get("default_model_version")
except Exception:
    st.error("Unable to load model metadata")
    st.stop()


# Load supported model definitions

try:
    r = requests.get(f"{GATEWAY_API_URL}/configs/model-schemas/supported")
    supported_models = r.json()
except Exception:
    st.error("Unable to load supported model definitions")
    st.stop()


# Select model version

if not available_model_versions:
    st.warning("No model versions available")
    st.stop()


selected_model_version = st.selectbox(
    "Select Model Schema Version",
    options=available_model_versions,
    index=available_model_versions.index(default_model_version)
    if default_model_version in available_model_versions
    else 0,
)


# Load selected schema

try:
    r = requests.get(
        f"{GATEWAY_API_URL}/configs/model-schemas/{selected_model_version}"
    )
    selected_schema = r.json()
    schema_model_type = selected_schema["model"]["type"]
    schema_params = selected_schema["model"]["params"]
except Exception:
    st.error("Unable to load selected model schema")
    st.stop()


st.info(f"Default Model Version: {default_model_version}")
st.info(f"Model Type: {schema_model_type}")

st.divider()


# Initialize session state

if "model_builder_type" not in st.session_state:
    st.session_state.model_builder_type = None

if "model_builder_params" not in st.session_state:
    st.session_state.model_builder_params = {}


# Load schema into builder

if st.button("Load Selected Version for Editing"):
    st.session_state.model_builder_type = schema_model_type
    st.session_state.model_builder_params = schema_params.copy()
    st.success("Model schema loaded into editor")


st.divider()
st.subheader("Create / Modify Model Schema")


# Select model type

model_type_options = list(supported_models.keys())

selected_model_type = st.selectbox(
    "Select Model Type",
    options=model_type_options,
    index=model_type_options.index(st.session_state.model_builder_type)
    if st.session_state.model_builder_type in model_type_options
    else 0,
)

st.session_state.model_builder_type = selected_model_type


# Build dynamic parameter form

model_definition = supported_models[selected_model_type]
parameters = model_definition["parameters"]

st.subheader("Hyperparameters")

new_params = {}

for param_name, param_meta in parameters.items():

    default_value = param_meta["default"]
    param_type = param_meta["type"]

    current_value = st.session_state.model_builder_params.get(
        param_name,
        default_value
    )

    if param_type == "int":
        value = st.number_input(
            param_name,
            value=int(current_value),
            step=1,
            key=f"param_{param_name}",
        )

    elif param_type == "float":
        value = st.number_input(
            param_name,
            value=float(current_value),
            format="%.6f",
            key=f"param_{param_name}",
        )

    elif param_type == "bool":
        value = st.checkbox(
            param_name,
            value=bool(current_value),
            key=f"param_{param_name}",
        )

    else:
        value = st.text_input(
            param_name,
            value=str(current_value),
            key=f"param_{param_name}",
        )

    new_params[param_name] = value


st.session_state.model_builder_params = new_params


st.divider()

st.subheader("Working Model Schema")

st.json({
    "type": st.session_state.model_builder_type,
    "params": st.session_state.model_builder_params,
})


# Create new version

if st.button("Create New Model Version"):

    payload = {
        "type": st.session_state.model_builder_type,
        "params": st.session_state.model_builder_params,
    }

    r = requests.post(
        f"{GATEWAY_API_URL}/configs/model-schemas",
        json=payload,
    )

    if r.status_code == 200:
        version = r.json()["model_schema_version"]
        st.success(f"Model version {version} created")
        st.session_state.model_builder_params = {}
        st.session_state.model_builder_type = None
        st.rerun()
    else:
        st.error(r.text)


# Set default model version

st.divider()

if st.button("Set Selected Version as Default"):

    r = requests.post(
        f"{GATEWAY_API_URL}/configs/model-schemas/default",
        params={"version": selected_model_version},
    )

    if r.status_code == 200:
        st.success("Default model version updated")
        st.rerun()
    else:
        st.error(r.text)
