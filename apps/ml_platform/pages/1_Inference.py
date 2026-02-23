import requests
import streamlit as st
import re
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


st.session_state.setdefault("inference_pending", False)
st.session_state.setdefault("inference_last_payload", None)
st.session_state.setdefault("inference_last_error", None)
st.session_state.setdefault("inference_last_result", None)

def _is_optional_value_set(widget_key: str, value) -> bool:
    """Return True once the user has changed this optional widget at least once.

    In Streamlit forms, widget values only update on submit, and callbacks are
    not supported reliably. We therefore detect changes by comparing the value
    to the last seen value across runs.
    """
    touched_key = f"{widget_key}__touched"
    prev_key = f"{widget_key}__prev"

    if prev_key not in st.session_state:
        st.session_state[prev_key] = value
        st.session_state.setdefault(touched_key, False)
        return False

    if value != st.session_state.get(prev_key):
        st.session_state[touched_key] = True
        st.session_state[prev_key] = value

    return bool(st.session_state.get(touched_key, False))

def _resolve_field_schema(field_schema: dict) -> dict:
    """Resolve optional fields encoded as anyOf[..., {"type": "null"}]."""
    if "anyOf" not in field_schema:
        return field_schema

    variants = field_schema.get("anyOf", [])
    non_null_variants = [
        variant for variant in variants
        if variant.get("type") != "null"
    ]

    if len(non_null_variants) == 1:
        merged = non_null_variants[0].copy()
        # Keep top-level metadata if present
        for key in ("title", "description"):
            if key in field_schema and key not in merged:
                merged[key] = field_schema[key]
        return merged

    return field_schema


def _render_field(field_name: str, field_schema: dict, is_required: bool):
    resolved_schema = _resolve_field_schema(field_schema)
    label = field_name + (" *" if is_required else "")

    field_type = resolved_schema.get("type")
    enum_values = resolved_schema.get("enum")
    minimum = resolved_schema.get("minimum")
    maximum = resolved_schema.get("maximum")
    pattern = resolved_schema.get("pattern")

    # Literal / enum
    if enum_values:
        if is_required:
            return st.selectbox(label, enum_values, key=f"inference_{field_name}")

        options = [""] + list(enum_values)
        selected = st.selectbox(label, options, key=f"inference_{field_name}")
        return None if selected == "" else selected

    # Integer
    if field_type == "integer":
        min_int = int(minimum) if minimum is not None else None
        max_int = int(maximum) if maximum is not None else None
        widget_key = f"inference_{field_name}"

        if is_required:
            default_value = min_int if min_int is not None else 0
            if max_int is not None and default_value > max_int:
                default_value = max_int

            int_kwargs = {
                "label": label,
                "step": 1,
                "value": default_value,
                "key": widget_key,
            }
            if min_int is not None:
                int_kwargs["min_value"] = min_int
            if max_int is not None:
                int_kwargs["max_value"] = max_int

            return int(
                st.number_input(**int_kwargs)
            )

        default_optional = min_int if min_int is not None else 0
        if max_int is not None and default_optional > max_int:
            default_optional = max_int

        optional_int_kwargs = {
            "label": label,
            "step": 1,
            "value": default_optional,
            "key": widget_key,
        }
        if min_int is not None:
            optional_int_kwargs["min_value"] = min_int
        if max_int is not None:
            optional_int_kwargs["max_value"] = max_int

        value = int(st.number_input(**optional_int_kwargs))
        return value if _is_optional_value_set(widget_key, value) else None

    # Float
    if field_type == "number":
        min_float = float(minimum) if minimum is not None else None
        max_float = float(maximum) if maximum is not None else None
        widget_key = f"inference_{field_name}"

        if is_required:
            default_value = min_float if min_float is not None else 0.0
            if max_float is not None and default_value > max_float:
                default_value = max_float

            float_kwargs = {
                "label": label,
                "step": 0.01,
                "value": default_value,
                "key": widget_key,
            }
            if min_float is not None:
                float_kwargs["min_value"] = min_float
            if max_float is not None:
                float_kwargs["max_value"] = max_float

            return float(
                st.number_input(**float_kwargs)
            )

        default_optional = min_float if min_float is not None else 0.0
        if max_float is not None and default_optional > max_float:
            default_optional = max_float

        optional_float_kwargs = {
            "label": label,
            "step": 0.01,
            "value": default_optional,
            "key": widget_key,
        }
        if min_float is not None:
            optional_float_kwargs["min_value"] = min_float
        if max_float is not None:
            optional_float_kwargs["max_value"] = max_float

        value = float(st.number_input(**optional_float_kwargs))
        return value if _is_optional_value_set(widget_key, value) else None

    # String
    if field_type == "string":
        value = st.text_input(label, key=f"inference_{field_name}")
        if pattern and value:
            if not re.match(pattern, value):
                st.warning(f"{field_name} format invalid")
        return value if value.strip() else None

    # Fallback
    value = st.text_input(label, key=f"inference_{field_name}")
    return value if value.strip() else None


def generate_form_from_schema(schema: dict):

    properties = schema.get("properties", {})
    required_fields = set(schema.get("required", []))

    payload = {}

    for field_name, field_schema in properties.items():
        payload[field_name] = _render_field(
            field_name,
            field_schema,
            is_required=(field_name in required_fields),
        )

    return payload, list(required_fields)
    

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
            st.session_state.inference_last_error = (
                f"Missing required fields: {missing}"
            )
            st.session_state.inference_pending = False
            st.session_state.inference_last_result = None
        else:
            st.session_state.inference_last_error = None
            st.session_state.inference_last_payload = payload
            st.session_state.inference_pending = True


if st.session_state.inference_pending and st.session_state.inference_last_payload:
    with st.spinner("Running prediction..."):
        try:
            response = requests.post(
                f"{GATEWAY_API_URL}/predict",
                json=st.session_state.inference_last_payload,
                headers=auth_headers(),
                timeout=10,
            )

            if response.status_code == 200:
                st.session_state.inference_last_result = response.json()
                st.session_state.inference_last_error = None
            else:
                st.session_state.inference_last_result = None
                if response.status_code in (401, 403):
                    st.session_state.inference_last_error = "Authentication required."
                else:
                    st.session_state.inference_last_error = response.text

        except Exception as exc:
            st.session_state.inference_last_result = None
            st.session_state.inference_last_error = f"Request error: {exc}"
        finally:
            st.session_state.inference_pending = False


if st.session_state.inference_last_error:
    st.error(st.session_state.inference_last_error)


if st.session_state.inference_last_result:
    result = st.session_state.inference_last_result
    prediction_value = result.get("prediction")

    st.success("Prediction successful")

    if prediction_value is not None:
        try:
            prediction_value = round(float(prediction_value), 2)
        except Exception:
            pass

    st.metric(
        label=f"Predicted {target_name}",
        value=prediction_value,
    )

    with st.expander("Full API response"):
        st.json(result)

with st.expander("Technical details"):
    st.write(f"Endpoint: {GATEWAY_API_URL}/predict")