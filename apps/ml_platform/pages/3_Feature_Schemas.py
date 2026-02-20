# Admin - Feature Schema Management

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

st.title("Feature Schema Admin")


# Load feature versions metadata

try:
    r = requests.get(
        f"{GATEWAY_API_URL}/configs/feature-schemas",
        headers=auth_headers(),
    )
    assert_response_ok(r, admin_only=True)
    feature_meta = r.json()
    active_contract_version = feature_meta.get("data_contract")
    available_feature_versions = feature_meta.get("available_feature_versions", [])
    default_feature_version = feature_meta.get("default_feature_version")
except Exception:
    st.error("Unable to load feature metadata")
    st.stop()


# Select feature version to view/edit

selected_feature_version = st.selectbox(
    "Select Feature Schema Version",
    options=available_feature_versions,
    index=available_feature_versions.index(default_feature_version)
    if default_feature_version in available_feature_versions
    else 0,
)

# Load selected feature schema

try:
    r = requests.get(
        f"{GATEWAY_API_URL}/configs/feature-schemas/{selected_feature_version}",
        headers=auth_headers(),
    )
    assert_response_ok(r, admin_only=True)
    selected_schema = r.json()
    schema_contract_version = selected_schema["data_contract"]
    schema_features = selected_schema.get("tabular_features", {})
except Exception:
    st.error("Unable to load selected feature schema")
    st.stop()


st.info(f"Default Feature Version: {default_feature_version}")
st.info(f"Schema Contract Version: {schema_contract_version}")

st.divider()


# Initialize session state

if "feature_builder" not in st.session_state:
    st.session_state.feature_builder = {}

if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False


# Load schema into builder

if st.button("Load Selected Version for Editing"):
    st.session_state.feature_builder = schema_features.copy()
    st.session_state.edit_mode = True
    st.success("Schema loaded into editor")


# Load data contract of schema

try:
    r = requests.get(
        f"{GATEWAY_API_URL}/configs/data-contract/{schema_contract_version}",
        headers=auth_headers(),
    )
    assert_response_ok(r, admin_only=True)
    contract = r.json()
    columns = contract["columns"]
except Exception:
    st.error("Unable to load related data contract")
    st.stop()


st.divider()
st.subheader("Add / Modify Features")


selected_column = st.selectbox(
    "Select column",
    options=list(columns.keys())
)

contract_type = columns[selected_column]["type"]
feature_config = {}


# Numeric handling

if contract_type in ["int", "float"]:
    feature_config["type"] = "numeric"

    impute = st.selectbox("Impute", ["none", "mean", "median"])
    scaler = st.selectbox("Scaler", ["none", "standard", "minmax"])

    if impute != "none":
        feature_config["impute"] = impute

    if scaler != "none":
        feature_config["scaler"] = scaler


# Categorical handling

elif contract_type == "string":
    feature_config["type"] = "categorical"

    allowed_values = columns[selected_column].get("allowed_values")

    encoding_options = ["onehot"]

    if allowed_values:
        encoding_options.append("ordinal")

        if len(allowed_values) == 2:
            encoding_options.append("binary")

    encoding = st.selectbox("Encoding", encoding_options)
    feature_config["encoding"] = encoding

    if encoding == "ordinal":
        st.info("Define numeric order (0 = lowest category)")

        order_mapping = {}

        for value in allowed_values:
            order_mapping[value] = st.number_input(
                f"Index for '{value}'",
                min_value=0,
                max_value=len(allowed_values) - 1,
                step=1,
                key=f"{selected_column}_{value}",
            )

        indexes = list(order_mapping.values())

        if len(set(indexes)) == len(allowed_values) and \
           sorted(indexes) == list(range(len(allowed_values))):

            ordered_values = [
                v for v, _ in sorted(order_mapping.items(), key=lambda x: x[1])
            ]
            feature_config["order"] = ordered_values
        else:
            st.warning("Indexes must be unique and sequential")

    if encoding == "binary":
        feature_config["values"] = allowed_values
        st.info(f"{allowed_values[0]} → 0 | {allowed_values[1]} → 1")


# Add or update feature

if st.button("Add / Update Feature"):

    if feature_config.get("encoding") == "ordinal" and "order" not in feature_config:
        st.warning("Complete ordinal configuration first")
        st.stop()

    st.session_state.feature_builder[selected_column] = feature_config
    st.success(f"{selected_column} added/updated")


st.divider()

st.subheader("Working Feature Schema")
st.json(st.session_state.feature_builder)


# Save as new version

if st.button("Create New Feature Version"):

    if not st.session_state.feature_builder:
        st.warning("No features defined")
        st.stop()

    payload = {
        "data_contract_version": schema_contract_version,
        "tabular_features": st.session_state.feature_builder,
    }

    r = requests.post(
        f"{GATEWAY_API_URL}/configs/feature-schemas",
        json=payload,
        headers=auth_headers(),
    )

    if r.status_code == 200:
        version = r.json()["feature_schema_version"]
        st.success(f"Feature version {version} created")
        st.session_state.feature_builder = {}
        st.session_state.edit_mode = False
        st.rerun()
    else:
        if r.status_code in (401, 403):
            assert_response_ok(r, admin_only=True)
        st.error(r.text)
