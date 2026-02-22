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

st.title("Model Inference")

# Retrieve schema (contains model_version + target + input_schema)

try:
    schema_response = requests.get(
        f"{GATEWAY_API_URL}/schema",
        headers=auth_headers(),
        timeout=3
    )

    assert_response_ok(schema_response)
    schema_payload = schema_response.json()

except Exception:
    st.error("Unable to retrieve model schema from API.")
    st.stop()

model_version = schema_payload.get("model_version")
target_name = schema_payload.get("target", "Prediction")
input_schema = schema_payload.get("input_schema", {})

st.success(f"Model version: {model_version}")
st.info(f"Predicting target: {target_name}")

def generate_form_from_schema(schema: dict):

    properties = schema.get("properties", {})
    required_fields = schema.get("required", [])

    payload = {}

    for field_name, field_schema in properties.items():

        is_required = field_name in required_fields
        label = field_name + (" *" if is_required else "")
        field_type = field_schema.get("type")

        if "enum" in field_schema:
            options = field_schema["enum"]
            if not is_required:
                options = [""] + options

            value = st.selectbox(label, options)
            payload[field_name] = None if value == "" else value

        elif field_type == "integer":
            if is_required:
                payload[field_name] = st.number_input(label, step=1)
            else:
                value = st.text_input(label)
                payload[field_name] = int(value) if value.strip() else None

        elif field_type == "number":
            if is_required:
                payload[field_name] = st.number_input(label, step=0.01)
            else:
                value = st.text_input(label)
                payload[field_name] = float(value) if value.strip() else None

        else:
            value = st.text_input(label)
            payload[field_name] = value if value.strip() else None

    return payload, required_fields


st.subheader("Input Features")

with st.form("prediction_form"):

    payload, required_fields = generate_form_from_schema(input_schema)
    submitted = st.form_submit_button("Predict")

    if submitted:

        missing = [
            f for f in required_fields
            if payload.get(f) in (None, "")
        ]

        if missing:
            st.error(f"Missing required fields: {missing}")
            st.stop()

        try:
            response = requests.post(
                f"{GATEWAY_API_URL}/predict",
                json=payload,
                headers=auth_headers(),
                timeout=10
            )

            if response.status_code == 200:

                result = response.json()
                prediction_value = result.get("prediction")

                st.success("Prediction successful")

                if prediction_value is not None:
                    try:
                        prediction_value = round(float(prediction_value), 2)
                    except Exception:
                        pass

                st.metric(
                    label=f"Predicted {target_name}",
                    value=prediction_value
                )

                with st.expander("Full API response"):
                    st.json(result)

            else:
                if response.status_code in (401, 403):
                    st.error("Authentication required.")
                else:
                    st.error(response.text)

        except Exception as e:
            st.error(f"Request error: {e}")

with st.expander("Technical details"):
    st.write(f"Endpoint: {GATEWAY_API_URL}/predict")