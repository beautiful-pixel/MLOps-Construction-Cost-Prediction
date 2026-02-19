import requests
import streamlit as st


st.set_page_config(
    page_title="Construction Cost Predictor",
    page_icon="🏠",
    layout="wide",
)

st.markdown(
    """
    <style>
        .stApp {
            background: radial-gradient(circle at 20% 20%, #0F3B4A 0%, #0B1D2A 55%, #08131B 100%);
        }
        .satellite-card {
            background: rgba(18, 43, 58, 0.7);
            border: 1px solid rgba(110, 198, 184, 0.35);
            border-radius: 14px;
            padding: 18px 20px;
            box-shadow: 0 10px 24px rgba(0,0,0,0.25);
        }
        .badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 999px;
            background: rgba(110, 198, 184, 0.2);
            color: #9CE4D9;
            font-size: 12px;
            margin-left: 8px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🏠 Construction Cost Estimator")
st.caption("Estimate construction costs using satellite-inspired features.")

with st.sidebar:
    st.header("API Settings")
    api_url = st.text_input("Predict endpoint URL", value="http://localhost:8000/predict")
    st.markdown("---")
    st.subheader("Version")
    st.write("1.0.0")

col_left, col_right = st.columns([1.2, 0.8], gap="large")

with col_left:
    st.subheader("Project details")

    with st.form("prediction-form"):
        st.markdown("#### Categories")
        seismic_hazard_zone = st.selectbox(
            "Seismic hazard zone",
            ["Moderate", "Low", "High"],
            index=0,
        )
        koppen_climate_zone_labels = {
            "cwb": "Temperate",
            "dfb": "Continental",
            "am": "Monsoon",
            "aw": "Savanna",
            "dfa": "Humid",
            "cfa": "Subtropical",
        }
        koppen_climate_zone = st.selectbox(
            "Climate",
            list(koppen_climate_zone_labels.keys()),
            index=0,
            format_func=koppen_climate_zone_labels.get,
        )
        tropical_cyclone_wind_risk = st.selectbox(
            "Tropical cyclone wind risk",
            ["Very high", "Moderate", "Low"],
            index=0,
        )
        flood_risk_class = st.selectbox("Flood risk?", ["Yes", "No"], index=0)
        country = st.selectbox("Country", ["Philippines"], index=0)
        tornadoes_wind_risk = st.selectbox("Tornado wind risk", ["Very low"], index=0)
        region_economic_classification = st.selectbox(
            "Regional income level",
            ["Low income", "Lower-middle income", "Upper-middle income", "High income"],
            index=0,
        )

        st.markdown("#### Binary features")
        developed_country = st.selectbox("Developed country?", ["Yes", "No"], index=0)
        landlocked = st.selectbox("Landlocked?", ["Yes", "No"], index=0)
        access_to_highway = st.selectbox("Access to highway?", ["Yes", "No"], index=0)
        access_to_railway = st.selectbox("Access to railway?", ["Yes", "No"], index=0)
        access_to_port = st.selectbox("Access to port?", ["Yes", "No"], index=0)
        access_to_airport = st.selectbox("Access to airport?", ["Yes", "No"], index=0)

        st.markdown("#### Numeric features")
        us_cpi = st.number_input("US CPI", min_value=0.0, value=302.1, step=0.1)
        deflated_gdp_usd = st.number_input("Deflated GDP (USD)", min_value=0.0001, value=26.8, step=0.1)
        year = st.number_input("Year", min_value=1900, max_value=2100, value=2023, step=1)
        straight_distance_to_capital_km = st.number_input(
            "Distance to capital (km)",
            min_value=0.0,
            value=45.7,
            step=0.1,
        )
        infrastructure_score = st.slider("Infrastructure score", min_value=0.0, max_value=1.0, value=0.62)
        distance_infra_interaction = st.number_input(
            "Distance x infrastructure interaction",
            min_value=0.0,
            value=12.3,
            step=0.1,
        )
        dev_high_seismic = st.selectbox("High seismic development indicator", [0, 1], index=1)
        dev_high_flood = st.selectbox("High flood development indicator", [0, 1], index=1)

        submitted = st.form_submit_button("Run prediction")

with col_right:
    st.subheader("Result")
    st.caption("Prediction is computed by the FastAPI service.")

    if submitted:
        def _normalize_value(value: str) -> str:
            return value.strip().lower()

        payload = {
            "seismic_hazard_zone": _normalize_value(seismic_hazard_zone),
            "koppen_climate_zone": koppen_climate_zone,
            "tropical_cyclone_wind_risk": _normalize_value(tropical_cyclone_wind_risk),
            "flood_risk_class": _normalize_value(flood_risk_class),
            "country": _normalize_value(country),
            "tornadoes_wind_risk": _normalize_value(tornadoes_wind_risk),
            "region_economic_classification": _normalize_value(region_economic_classification),
            "developed_country": _normalize_value(developed_country),
            "us_cpi": us_cpi,
            "infrastructure_score": infrastructure_score,
            "landlocked": _normalize_value(landlocked),
            "access_to_highway": _normalize_value(access_to_highway),
            "access_to_railway": _normalize_value(access_to_railway),
            "access_to_port": _normalize_value(access_to_port),
            "access_to_airport": _normalize_value(access_to_airport),
            "straight_distance_to_capital_km": straight_distance_to_capital_km,
            "distance_infra_interaction": distance_infra_interaction,
            "year": int(year),
            "dev_high_seismic": dev_high_seismic,
            "dev_high_flood": dev_high_flood,
            "deflated_gdp_usd": deflated_gdp_usd,
        }

        try:
            response = requests.post(api_url, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            prediction_value = result.get("prediction")
            if prediction_value is None:
                st.error("Unexpected response from the API.")
            else:
                st.metric("Predicted cost", f"{prediction_value:,.4f}")
                st.json(result)
        except requests.RequestException as exc:
            st.error("Cannot reach the API.")
            st.write(str(exc))

    else:
        st.info("Fill in the form, then click “Run prediction”.")

