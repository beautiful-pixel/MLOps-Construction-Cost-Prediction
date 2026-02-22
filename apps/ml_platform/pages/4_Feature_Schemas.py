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


# Load feature metadata

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


selected_feature_version = st.selectbox(
    "Select Feature Schema Version",
    options=available_feature_versions,
    index=available_feature_versions.index(default_feature_version)
    if default_feature_version in available_feature_versions
    else 0,
)

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


# Session state

if "feature_builder" not in st.session_state:
    st.session_state.feature_builder = {}

if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False


if st.button("Load Selected Version for Editing"):
    st.session_state.feature_builder = schema_features.copy()
    st.session_state.edit_mode = True
    st.success("Schema loaded into editor")


# Load data contract

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


configured_features = set(st.session_state.feature_builder.keys())


def format_column_label(col):
    if col in configured_features:
        return f"✔ {col}"
    return col


selected_column = st.selectbox(
    "Select column",
    options=list(columns.keys()),
    format_func=format_column_label,
)

contract_type = columns[selected_column]["type"]
is_nullable = not columns[selected_column].get("non_nullable", False)

existing_config = st.session_state.feature_builder.get(selected_column, {})
feature_config = existing_config.copy()


# Numeric features

if contract_type in ["int", "float"]:

    feature_config["type"] = "numeric"

    numeric_impute_options = ["mean", "median"]
    impute_options = numeric_impute_options if is_nullable else ["none"] + numeric_impute_options

    default_impute = feature_config.get("impute", "none")
    if default_impute not in impute_options:
        default_impute = impute_options[0]

    impute = st.selectbox(
        "Impute" + (" (required)" if is_nullable else ""),
        impute_options,
        index=impute_options.index(default_impute),
    )

    if impute != "none":
        feature_config["impute"] = impute
    else:
        feature_config.pop("impute", None)

    scaler_options = ["none", "standard", "minmax"]
    default_scaler = feature_config.get("scaler", "none")

    scaler = st.selectbox(
        "Scaler",
        scaler_options,
        index=scaler_options.index(default_scaler)
        if default_scaler in scaler_options
        else 0,
    )

    if scaler != "none":
        feature_config["scaler"] = scaler
    else:
        feature_config.pop("scaler", None)


# Categorical features

elif contract_type == "string":

    feature_config["type"] = "categorical"

    categorical_impute_options = ["most_frequent", "constant"]
    impute_options = categorical_impute_options if is_nullable else ["none"] + categorical_impute_options

    default_impute = feature_config.get("impute", "none")
    if default_impute not in impute_options:
        default_impute = impute_options[0]

    impute = st.selectbox(
        "Impute" + (" (required)" if is_nullable else ""),
        impute_options,
        index=impute_options.index(default_impute),
    )

    if impute != "none":
        feature_config["impute"] = impute

        if impute == "constant":
            default_fill = feature_config.get("fill_value", "")
            constant_value = st.text_input("Constant value for missing", value=default_fill)
            if constant_value:
                feature_config["fill_value"] = constant_value
    else:
        feature_config.pop("impute", None)
        feature_config.pop("fill_value", None)

    allowed_values = columns[selected_column].get("allowed_values")
    encoding_options = ["onehot"]

    if allowed_values:
        encoding_options.append("ordinal")
        if len(allowed_values) == 2:
            encoding_options.append("binary")

    default_encoding = feature_config.get("encoding", encoding_options[0])
    if default_encoding not in encoding_options:
        default_encoding = encoding_options[0]

    encoding = st.selectbox(
        "Encoding",
        encoding_options,
        index=encoding_options.index(default_encoding),
    )

    feature_config["encoding"] = encoding

    if encoding == "ordinal":

        st.info("Define numeric order (0 = lowest category)")

        existing_order = feature_config.get("order", allowed_values)
        order_mapping = {}

        for value in allowed_values:
            default_index = existing_order.index(value) if value in existing_order else 0
            order_mapping[value] = st.number_input(
                f"Index for '{value}'",
                min_value=0,
                max_value=len(allowed_values) - 1,
                step=1,
                value=default_index,
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


# Add / Update Feature

if st.button("Add / Update Feature"):

    if is_nullable and "impute" not in feature_config:
        st.warning("Imputation is required for nullable columns.")
        st.stop()

    if feature_config.get("encoding") == "ordinal" and "order" not in feature_config:
        st.warning("Complete ordinal configuration first")
        st.stop()

    st.session_state.feature_builder[selected_column] = feature_config
    st.success(f"{selected_column} added/updated")
    st.rerun()


# Delete Feature

if selected_column in st.session_state.feature_builder:
    if st.button("Delete Feature"):
        del st.session_state.feature_builder[selected_column]
        st.success(f"{selected_column} removed")
        st.rerun()


# Working Schema Display

st.divider()
st.subheader("Working Feature Schema")

if st.session_state.feature_builder:
    for col, cfg in st.session_state.feature_builder.items():
        st.write(f"**{col}** → {cfg}")
else:
    st.info("No features configured yet.")


# Save new version

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