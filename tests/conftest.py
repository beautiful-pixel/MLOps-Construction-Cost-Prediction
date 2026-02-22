import sys
from pathlib import Path
from datetime import datetime, timedelta
import os
import pandas as pd
import tempfile
import shutil
from unittest.mock import MagicMock

import pytest
from passlib.context import CryptContext
from jose import jwt
from fastapi.testclient import TestClient
import responses

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "api" / "gateway_api"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@pytest.fixture
def test_secret_key():
    return "test-secret-key-for-testing"


@pytest.fixture
def test_algorithm():
    return "HS256"


@pytest.fixture
def test_user_credentials():
    return {
        "username": "testuser",
        "password": "testpassword123",
        "role": "user"
    }


@pytest.fixture
def test_admin_credentials():
    return {
        "username": "testadmin",
        "password": "testadminpass123",
        "role": "admin"
    }


@pytest.fixture
def valid_jwt_token(test_secret_key, test_algorithm):
    payload = {
        "sub": "testuser",
        "role": "user",
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, test_secret_key, algorithm=test_algorithm)


@pytest.fixture
def expired_jwt_token(test_secret_key, test_algorithm):
    payload = {
        "sub": "testuser",
        "role": "user",
        "exp": datetime.utcnow() - timedelta(hours=1)
    }
    return jwt.encode(payload, test_secret_key, algorithm=test_algorithm)


@pytest.fixture
def hashed_password(test_user_credentials):
    return pwd_context.hash(test_user_credentials["password"])


@pytest.fixture
def hashed_admin_password(test_admin_credentials):
    return pwd_context.hash(test_admin_credentials["password"])


# ============================================================================
# DATA & FIXTURES
# ============================================================================

@pytest.fixture
def sample_dataframe():
    """Create a sample DataFrame for testing."""
    return pd.DataFrame({
        "data_id": ["ID001", "ID002", "ID003"],
        "country": ["France", "Germany", "Spain"],
        "year": [2020, 2021, 2022],
        "deflated_gdp_usd": [25.5, 28.3, 30.1],
        "us_cpi": [300.0, 310.0, 315.0],
        "developed_country": ["Yes", "Yes", "Yes"],
        "landlocked": ["No", "No", "Yes"],
        "region_economic_classification": ["High income", "High income", "High income"],
        "seismic_hazard_zone": ["Low", "Low", "Moderate"],
        "access_to_airport": ["Yes", "Yes", "Yes"],
        "access_to_highway": ["Yes", "Yes", "Yes"],
        "access_to_port": ["Yes", "No", "Yes"],
        "access_to_railway": ["Yes", "Yes", "Yes"],
        "flood_risk_class": ["Yes", "No", "Yes"],
        "straight_distance_to_capital_km": [45.5, 120.3, 85.1],
        "quarter_label": ["2020-Q1", "2021-Q2", "2022-Q3"],
    })


@pytest.fixture
def sample_invalid_dataframe():
    """Create an invalid DataFrame for testing validation."""
    return pd.DataFrame({
        "data_id": ["ID001", "ID002", None],  # Missing required field
        "country": ["France", "Germany", "Spain"],
        "year": [2020, 2021, 99999],  # Invalid year
        "deflated_gdp_usd": [-5.0, 28.3, 30.1],  # Negative value
    })


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for data testing."""
    temp_dir = tempfile.mkdtemp(prefix="test_data_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_incoming_dir(temp_data_dir):
    """Create a temporary incoming directory structure."""
    incoming_dir = temp_data_dir / "incoming"
    incoming_dir.mkdir(parents=True, exist_ok=True)
    yield incoming_dir


@pytest.fixture
def temp_raw_dir(temp_data_dir):
    """Create a temporary raw data directory."""
    raw_dir = temp_data_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    yield raw_dir


@pytest.fixture
def sample_csv_file(temp_incoming_dir, sample_dataframe):
    """Create a sample CSV file in incoming directory."""
    csv_path = temp_incoming_dir / "data_sample.csv"
    sample_dataframe.to_csv(csv_path, index=False)
    return csv_path


@pytest.fixture
def inference_payload():
    """Standard inference API payload."""
    return {
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


# ============================================================================
# API CLIENT FIXTURES
# ============================================================================

@pytest.fixture
def test_http_client():
    """Create an HTTP client for API testing."""
    from httpx import Client
    with Client() as client:
        yield client


@pytest.fixture
@responses.activate
def mock_http_responses():
    """Setup responses mock for HTTP calls."""
    return responses


# ============================================================================
# DATABASE & MOCK FIXTURES
# ============================================================================

@pytest.fixture
def mock_db_connection():
    """Mock database connection."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn


@pytest.fixture
def mock_mlflow_client():
    """Mock MLflow client."""
    mock_client = MagicMock()
    mock_client.set_experiment.return_value = "test_experiment_id"
    mock_client.log_metrics.return_value = None
    mock_client.log_params.return_value = None
    return mock_client


@pytest.fixture
def mock_airflow_dag():
    """Mock Airflow DAG."""
    mock_dag = MagicMock()
    mock_dag.dag_id = "test_dag"
    mock_dag.tasks = []
    return mock_dag


# ============================================================================
# CONFIGURATION FIXTURES
# ============================================================================

@pytest.fixture
def sample_data_contract():
    """Sample data contract configuration."""
    return {
        "version": 1,
        "tabular_extensions": ["csv"],
        "image_extensions": ["tif"],
        "columns": {
            "data_id": {
                "type": "string",
                "non_nullable": True,
            },
            "country": {
                "type": "string",
                "non_nullable": True,
            },
            "year": {
                "type": "int",
                "min": 1950,
                "max": 2100,
                "non_nullable": True,
            },
            "deflated_gdp_usd": {
                "type": "float",
                "min": 0,
            },
        },
        "primary_key": ["data_id"],
        "target": None,
    }


@pytest.fixture
def sample_feature_schema():
    """Sample feature schema configuration."""
    return {
        "version": 1,
        "data_contract": 1,
        "tabular_features": {
            "deflated_gdp_usd": {
                "type": "numeric",
                "impute": "median",
            },
            "straight_distance_to_capital_km": {
                "type": "numeric",
                "impute": "median",
                "clip": [0, 5000],
            },
            "developed_country": {
                "type": "categorical",
                "encoding": "binary",
                "impute": "most_frequent",
            },
        },
    }


@pytest.fixture
def sample_model_schema():
    """Sample model schema configuration."""
    return {
        "version": 1,
        "feature_version": 1,
        "model_type": "RandomForestRegressor",
        "hyperparameters": {
            "n_estimators": 100,
            "max_depth": 10,
            "random_state": 42,
        },
    }


@pytest.fixture
def sample_split_schema():
    """Sample split schema configuration."""
    return {
        "version": 1,
        "data_contract": 1,
        "strategy": "geographic",
        "parameters": {
            "train_ratio": 0.7,
            "test_ratio": 0.2,
            "reference_ratio": 0.1,
        },
    }
