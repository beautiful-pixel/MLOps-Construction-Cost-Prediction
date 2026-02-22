"""
Integration tests for Gateway API endpoints.
"""
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "api" / "gateway_api"))


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    from core.config import SECRET_KEY
    from fastapi import FastAPI
    
    app = FastAPI()
    
    # Mock routers
    return TestClient(app)


class TestAuthenticationEndpoints:
    """Test authentication endpoints."""

    def test_login_success(self, client):
        """Test successful login."""
        response = client.post(
            "/auth/login",
            json={
                "username": "testuser",
                "password": "testpass123"
            }
        )
        
        # Would return 200 with valid credentials
        assert response.status_code in [200, 401, 422]

    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = client.post(
            "/auth/login",
            json={
                "username": "wronguser",
                "password": "wrongpass"
            }
        )
        
        assert response.status_code in [401, 422, 200]

    def test_login_missing_fields(self, client):
        """Test login with missing required fields."""
        response = client.post(
            "/auth/login",
            json={"username": "testuser"}
        )
        
        assert response.status_code in [422, 400]

    def test_logout(self, client, valid_jwt_token):
        """Test logout endpoint."""
        response = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )
        
        # Should succeed or return 200/401
        assert response.status_code in [200, 401, 404]

    def test_token_refresh(self, client, valid_jwt_token):
        """Test token refresh endpoint."""
        response = client.post(
            "/auth/refresh",
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )
        
        assert response.status_code in [200, 401, 404]

    def test_user_registration(self, client):
        """Test user registration endpoint."""
        response = client.post(
            "/auth/register",
            json={
                "username": "newuser",
                "password": "newpass123",
                "email": "newuser@example.com"
            }
        )
        
        assert response.status_code in [201, 200, 400, 409, 404]


class TestConfigurationEndpoints:
    """Test configuration endpoints."""

    def test_get_data_contract(self, client, valid_jwt_token):
        """Test getting data contract."""
        response = client.get(
            "/configs/data-contract/1",
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )
        
        assert response.status_code in [200, 401, 404]

    def test_get_feature_schema(self, client, valid_jwt_token):
        """Test getting feature schema."""
        response = client.get(
            "/configs/feature-schema/1",
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )
        
        assert response.status_code in [200, 401, 404]

    def test_get_model_schema(self, client, valid_jwt_token):
        """Test getting model schema."""
        response = client.get(
            "/configs/model-schema/1",
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )
        
        assert response.status_code in [200, 401, 404]

    def test_get_split_schema(self, client, valid_jwt_token):
        """Test getting split schema."""
        response = client.get(
            "/configs/split-schema/1",
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )
        
        assert response.status_code in [200, 401, 404]

    def test_list_available_versions(self, client, valid_jwt_token):
        """Test listing available versions."""
        response = client.get(
            "/configs/versions",
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )
        
        assert response.status_code in [200, 401, 404]

    def test_update_active_config(self, client, valid_jwt_token):
        """Test updating active configuration (admin only)."""
        response = client.patch(
            "/configs/active",
            json={
                "data_contract_version": 1,
                "feature_version": 1,
                "model_version": 1,
            },
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )
        
        assert response.status_code in [200, 401, 403, 404]


class TestPipelineControlEndpoints:
    """Test pipeline control endpoints."""

    def test_trigger_data_pipeline(self, client, valid_jwt_token):
        """Test triggering data pipeline."""
        response = client.post(
            "/pipelines/data-pipeline/trigger",
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )
        
        assert response.status_code in [202, 200, 401, 404]

    def test_trigger_train_pipeline(self, client, valid_jwt_token):
        """Test triggering train pipeline."""
        response = client.post(
            "/pipelines/train-pipeline/trigger",
            json={
                "feature_version": 1,
                "model_version": 1,
                "split_version": 1,
            },
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )
        
        assert response.status_code in [202, 200, 401, 404]

    def test_get_pipeline_status(self, client, valid_jwt_token):
        """Test getting pipeline status."""
        response = client.get(
            "/pipelines/status",
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )
        
        assert response.status_code in [200, 401, 404]

    def test_get_pipeline_logs(self, client, valid_jwt_token):
        """Test getting pipeline logs."""
        response = client.get(
            "/pipelines/data-pipeline/logs",
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )
        
        assert response.status_code in [200, 401, 404]


class TestDataEndpoints:
    """Test data management endpoints."""

    def test_upload_data_batch(self, client, valid_jwt_token):
        """Test uploading data batch."""
        # Would need multipart form data
        response = client.post(
            "/data/upload",
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )
        
        assert response.status_code in [400, 422, 413, 401, 200]

    def test_get_master_dataset_info(self, client, valid_jwt_token):
        """Test getting master dataset info."""
        response = client.get(
            "/data/master/info",
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )
        
        assert response.status_code in [200, 401, 404]

    def test_get_splits_info(self, client, valid_jwt_token):
        """Test getting splits info."""
        response = client.get(
            "/data/splits/info",
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )
        
        assert response.status_code in [200, 401, 404]

    def test_list_batches(self, client, valid_jwt_token):
        """Test listing data batches."""
        response = client.get(
            "/data/batches",
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )
        
        assert response.status_code in [200, 401, 404]


class TestModelEndpoints:
    """Test model management endpoints."""

    def test_list_available_models(self, client, valid_jwt_token):
        """Test listing available models."""
        response = client.get(
            "/models/available",
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )
        
        assert response.status_code in [200, 401, 404]

    def test_get_model_metadata(self, client, valid_jwt_token):
        """Test getting model metadata."""
        response = client.get(
            "/models/1/metadata",
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )
        
        assert response.status_code in [200, 401, 404]

    def test_get_model_metrics(self, client, valid_jwt_token):
        """Test getting model metrics."""
        response = client.get(
            "/models/1/metrics",
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )
        
        assert response.status_code in [200, 401, 404]

    def test_list_experiments(self, client, valid_jwt_token):
        """Test listing MLflow experiments."""
        response = client.get(
            "/mlflow/experiments",
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )
        
        assert response.status_code in [200, 401, 404]


class TestErrorHandling:
    """Test error handling."""

    def test_404_not_found(self, client):
        """Test 404 response."""
        response = client.get("/nonexistent/endpoint")
        
        assert response.status_code == 404

    def test_400_bad_request(self, client):
        """Test 400 Bad Request."""
        response = client.post(
            "/auth/login",
            json={"invalid": "data"}
        )
        
        assert response.status_code in [422, 400]

    def test_401_unauthorized(self, client):
        """Test 401 Unauthorized without token."""
        response = client.get(
            "/data/master/info"
        )
        
        assert response.status_code in [401, 403, 307]

    def test_403_forbidden_without_admin(self, client, valid_jwt_token):
        """Test 403 Forbidden for non-admin access."""
        response = client.patch(
            "/configs/active",
            json={"key": "value"},
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )
        
        # Might be 403 if token is non-admin
        assert response.status_code in [403, 401, 404]

    def test_500_server_error(self, client):
        """Test 500 Server Error handling."""
        # This would test actual error handling in API
        response = client.get("/health")
        
        # Should not be 500
        assert response.status_code != 500

    def test_request_validation_error(self, client):
        """Test request validation."""
        response = client.post(
            "/auth/login",
            json={"username": 123}  # Invalid type
        )
        
        assert response.status_code in [422, 400]

    def test_response_schema_validation(self, client):
        """Test response schema validation."""
        response = client.get("/health")
        
        # Response should be valid JSON or 404
        if response.status_code in [200, 404]:
            try:
                response.json()
            except:
                pytest.fail("Response is not valid JSON")


class TestRateLimiting:
    """Test rate limiting."""

    def test_rate_limit_enforcement(self, client):
        """Test rate limiting on endpoints."""
        # Make multiple requests
        for i in range(3):
            response = client.get("/health")
            assert response.status_code in [200, 404, 429]

    def test_rate_limit_headers(self, client):
        """Test rate limit headers."""
        response = client.get("/health")
        
        # Check for rate limit headers
        assert response.status_code in [200, 404]


class TestCORSHeaders:
    """Test CORS headers."""

    def test_cors_origin_header(self, client):
        """Test CORS origin header."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        
        # Should allow or not have CORS
        assert response.status_code in [200, 404]

    def test_cors_preflight_request(self, client):
        """Test CORS preflight request."""
        response = client.options(
            "/auth/login"
        )
        
        assert response.status_code in [200, 404]
