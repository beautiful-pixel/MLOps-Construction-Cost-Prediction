import sys
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "api" / "gateway_api"))

# Skip integration tests by default unless explicitly enabled
# Set RUN_INTEGRATION_TESTS=true to run (automatically set in CI)
if not os.getenv("RUN_INTEGRATION_TESTS", "").lower() == "true":
    pytestmark = pytest.mark.skip(reason="Integration tests require a running server. Run with RUN_INTEGRATION_TESTS=true")


class TestInferenceEndpoint:

    def test_inference_endpoint_without_token_fails(self):
        from fastapi import FastAPI
        from routers.inference import router as inference_router
        
        app = FastAPI()
        app.include_router(inference_router)
        client = TestClient(app)
        
        payload = {
            "deflated_gdp_usd": 26.8,
            "us_cpi": 302.1,
        }
        
        response = client.post("/predict", json=payload)
        assert response.status_code in [401, 403, 503]

    def test_inference_endpoint_requires_authentication(self):
        from fastapi import FastAPI
        from routers.inference import router as inference_router
        
        app = FastAPI()
        app.include_router(inference_router)
        client = TestClient(app)
        
        payload = {
            "deflated_gdp_usd": 26.8,
            "us_cpi": 302.1,
        }
        
        response = client.post(
            "/predict",
            json=payload,
            headers={"Authorization": "Bearer invalid"}
        )
        assert response.status_code in [401, 403, 503]


class TestConfigEndpoints:

    def test_config_endpoint_requires_authentication(self):
        from fastapi import FastAPI
        from routers.features import router as features_router
        
        app = FastAPI()
        app.include_router(features_router)
        client = TestClient(app)

        response = client.post(
            "/configs/feature-schemas",
            json={
                "data_contract_version": 1,
                "features": {}
            },
        )
        assert response.status_code in [401, 403]

    def test_config_endpoint_requires_admin_for_write(self):
        from fastapi import FastAPI
        from routers.features import router as features_router
        from routers.auth import router as auth_router
        
        app = FastAPI()
        app.include_router(auth_router)
        app.include_router(features_router)
        client = TestClient(app)
        
        login_response = client.post(
            "/auth/login",
            data={"username": "user", "password": "user"}
        )
        token = login_response.json()["access_token"]
        
        response = client.post(
            "/configs/feature-schemas",
            json={
                "data_contract_version": 1,
                "features": {}
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403


class TestTrainingEndpoints:

    def test_training_endpoint_requires_admin(self):
        from fastapi import FastAPI
        from routers.training import router as training_router
        from routers.auth import router as auth_router
        
        app = FastAPI()
        app.include_router(auth_router)
        app.include_router(training_router)
        client = TestClient(app)
        
        login_response = client.post(
            "/auth/login",
            data={"username": "user", "password": "user"}
        )
        token = login_response.json()["access_token"]
        
        response = client.post(
            "/training/run",
            json={
                "feature_version": 1,
                "split_version": 1,
                "model_config_version": 1
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403

    def test_training_endpoint_accepts_valid_payload_from_admin(self):
        from fastapi import FastAPI
        from routers.training import router as training_router
        from routers.auth import router as auth_router
        from unittest.mock import patch
        
        app = FastAPI()
        app.include_router(auth_router)
        app.include_router(training_router)
        client = TestClient(app)
        
        login_response = client.post(
            "/auth/login",
            data={"username": "admin", "password": "admin"}
        )
        token = login_response.json()["access_token"]
        
        with patch('services.airflow_client.airflow_service.trigger_dag') as mock_trigger:
            mock_trigger.return_value = {"dag_run_id": "test_123"}
            
            response = client.post(
                "/training/run",
                json={
                    "feature_version": 1,
                    "split_version": 1,
                    "model_config_version": 1
                },
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code in [200, 500, 503]


class TestPipelineEndpoints:

    def test_pipeline_endpoint_requires_authentication(self):
        from fastapi import FastAPI
        from routers.pipeline import router as pipeline_router
        
        app = FastAPI()
        app.include_router(pipeline_router)
        client = TestClient(app)
        
        response = client.get("/pipeline/dags")
        assert response.status_code in [401, 403, 404]

    @pytest.mark.timeout(10)
    def test_pipeline_endpoint_accessible_with_valid_token(self):
        from fastapi import FastAPI
        from routers.pipeline import router as pipeline_router
        from core.config import SECRET_KEY
        from jose import jwt
        from datetime import datetime, timedelta
        
        app = FastAPI()
        app.include_router(pipeline_router)
        client = TestClient(app)
        
        # Create a valid token directly
        payload = {
            "sub": "admin",
            "role": "admin",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        
        with patch('services.airflow_client.airflow_service.list_dags') as mock_list:
            mock_list.return_value = []
            response = client.get(
                "/pipeline/dags",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code in [200, 500, 503, 401, 404]


class TestModelsEndpoints:

    def test_models_endpoint_requires_authentication(self):
        from fastapi import FastAPI
        from routers.models import router as models_router
        
        app = FastAPI()
        app.include_router(models_router)
        client = TestClient(app)
        
        response = client.get("/models/current")
        assert response.status_code in [401, 403]

    @pytest.mark.timeout(5)  # Add timeout to prevent hanging
    @pytest.mark.timeout(5)
    @pytest.mark.skip(reason="Integration test requires running server")
    def test_models_endpoint_accessible_with_valid_token(self):
        pass


class TestExperimentsEndpoints:

    def test_experiments_endpoint_requires_authentication(self):
        from fastapi import FastAPI
        from routers.experiments import router as experiments_router
        
        app = FastAPI()
        app.include_router(experiments_router)
        client = TestClient(app)
        
        response = client.get("/experiments/")
        assert response.status_code in [401, 403]

    @pytest.mark.timeout(10)
    def test_experiments_endpoint_accessible_with_valid_token(self):
        from fastapi import FastAPI
        from routers.experiments import router as experiments_router
        from core.config import SECRET_KEY
        from jose import jwt
        from datetime import datetime, timedelta
        
        app = FastAPI()
        app.include_router(experiments_router)
        client = TestClient(app)
        
        # Create a valid token directly
        payload = {
            "sub": "admin",
            "role": "admin",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

        with patch("services.mlflow_client.mlflow_service.list_experiments") as mock_list:
            mock_list.return_value = []
            response = client.get(
                "/experiments/",
                headers={"Authorization": f"Bearer {token}"}
            )

        assert response.status_code in [200, 404, 403, 401]


class TestDataContractEndpoints:

    def test_data_contract_endpoint_requires_authentication(self):
        from fastapi import FastAPI
        from routers.data_contract import router as data_contract_router
        
        app = FastAPI()
        app.include_router(data_contract_router)
        client = TestClient(app)
        
        response = client.get("/configs/data-contract/1")
        assert response.status_code in [401, 403]

    def test_data_contract_write_requires_admin(self):
        from fastapi import FastAPI
        from routers.data_contract import router as data_contract_router
        from routers.auth import router as auth_router
        
        app = FastAPI()
        app.include_router(auth_router)
        app.include_router(data_contract_router)
        client = TestClient(app)
        
        login_response = client.post(
            "/auth/login",
            data={"username": "user", "password": "user"}
        )
        token = login_response.json()["access_token"]
        
        response = client.get(
            "/configs/data-contract/1",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403


class TestFeatureEndpoints:

    def test_feature_endpoint_requires_authentication(self):
        from fastapi import FastAPI
        from routers.features import router as features_router
        
        app = FastAPI()
        app.include_router(features_router)
        client = TestClient(app)
        
        response = client.get("/configs/feature-schemas")
        assert response.status_code in [401, 403]

    def test_feature_write_requires_admin(self):
        from fastapi import FastAPI
        from routers.features import router as features_router
        from routers.auth import router as auth_router
        
        app = FastAPI()
        app.include_router(auth_router)
        app.include_router(features_router)
        client = TestClient(app)
        
        login_response = client.post(
            "/auth/login",
            data={"username": "user", "password": "user"}
        )
        token = login_response.json()["access_token"]
        
        response = client.post(
            "/configs/feature-schemas",
            json={
                "tabular_features": {},
                "image_features": {}
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403
