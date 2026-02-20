import os
import requests

payload = {
    "deflated_gdp_usd": 26.8,
    "us_cpi": 302.1,
    "straight_distance_to_capital_km": 45.7,
    "developed_country": "No",
    "landlocked": "No",
    "access_to_highway": "Yes",
    "access_to_railway": "Yes",
    "access_to_port": "Yes",
    "access_to_airport": "Yes",
    "flood_risk_class": "Yes",
    "region_economic_classification": "Lower-middle income",
    "seismic_hazard_zone": "Moderate",
}

INFERENCE_API_URL = os.getenv("INFERENCE_API_URL")
if not INFERENCE_API_URL:
    raise SystemExit("INFERENCE_API_URL is not set.")

response = requests.post(
    f"{INFERENCE_API_URL}/predict",
    json=payload,
)

print(response.json())
