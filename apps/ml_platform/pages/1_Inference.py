import requests
import streamlit as st
from streamlit_auth import (
    assert_response_ok,
    auth_headers,
    get_gateway_api_url,
    require_auth,
)


# Configuration

GATEWAY_API_URL = get_gateway_api_url()
require_auth()



st.title("Model Inference")


# Health check

try:
    health_response = requests.get(
        f"{GATEWAY_API_URL}/info",
        headers=auth_headers(),
        timeout=3
    )

    if health_response.status_code == 200:
        health_data = health_response.json()

        st.success(
            f"API healthy | "
            f"Model version: {health_data.get('model_version')} | "
            f"Feature version: {health_data.get('feature_version')}"
        )
    elif health_response.status_code in (401, 403):
        st.error(
            "Authentication required. "
            "Login with user / user123 or admin / admin."
        )
        st.stop()
    elif health_response.status_code == 404:
        st.warning("No production model found.")
        st.stop()
    else:
        st.error("API reachable but unhealthy.")
        st.stop()

except Exception:
    st.error("Gateway API not reachable.")
    st.stop()


# Retrieve dynamic schema

try:
    schema_response = requests.get(
        f"{GATEWAY_API_URL}/schema",
        headers=auth_headers(),
        timeout=3
    )

    assert_response_ok(schema_response)

    model_schema = schema_response.json()

except Exception:
    st.error("Unable to retrieve model schema from API.")
    st.stop()


# Generate form from schema

def generate_form_from_schema(schema: dict):

    properties = schema.get("properties", {})
    required_fields = schema.get("required", [])

    payload = {}

    for field_name, field_schema in properties.items():

        is_required = field_name in required_fields

        label = field_name
        if is_required:
            label += " *"

        field_type = field_schema.get("type")

        # Enum fields
        if "enum" in field_schema:

            options = field_schema["enum"]

            if not is_required:
                options = [""] + options

            value = st.selectbox(label, options)

            if value == "":
                payload[field_name] = None
            else:
                payload[field_name] = value

        # Integer fields
        elif field_type == "integer":

            if is_required:
                payload[field_name] = st.number_input(
                    label,
                    step=1
                )
            else:
                value = st.text_input(label)
                payload[field_name] = int(value) if value.strip() != "" else None

        # Float fields
        elif field_type == "number":

            if is_required:
                payload[field_name] = st.number_input(
                    label,
                    step=0.01
                )
            else:
                value = st.text_input(label)
                payload[field_name] = float(value) if value.strip() != "" else None

        # String fields
        else:

            value = st.text_input(label)

            if not is_required and value.strip() == "":
                payload[field_name] = None
            else:
                payload[field_name] = value

    return payload


# Prediction form

st.subheader("Input Features")

with st.form("prediction_form"):

    payload = generate_form_from_schema(model_schema)

    submitted = st.form_submit_button("Predict")

    if submitted:

        try:
            response = requests.post(
                f"{GATEWAY_API_URL}/predict",
                json=payload,
                headers=auth_headers(),
                timeout=10
            )

            if response.status_code == 200:

                result = response.json()

                st.success("Prediction successful")

                st.metric(
                    label="Predicted Value",
                    value=result.get("prediction")
                )

                st.json(result)

            else:
                if response.status_code in (401, 403):
                    st.error(
                        "Authentication required. "
                        "Login with user / user123 or admin / admin."
                    )
                else:
                    st.error(response.text)

        except Exception as e:
            st.error(f"Request error: {e}")


with st.expander("API Details"):
    st.write(f"Endpoint: {GATEWAY_API_URL}/predict")
