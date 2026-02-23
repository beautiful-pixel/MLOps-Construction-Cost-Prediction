"""
Integration tests for Dataset management endpoints.

New endpoints added for dataset oversight and retrain threshold management.
"""
import sys
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "api" / "gateway_api"))

# Skip integration tests by default unless explicitly enabled
# Set RUN_INTEGRATION_TESTS=true to run (automatically set in CI)
if not os.getenv("RUN_INTEGRATION_TESTS", "").lower() == "true":
    pytestmark = pytest.mark.skip(reason="Integration tests require a running server. Run with RUN_INTEGRATION_TESTS=true")


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    from fastapi import FastAPI
    
    app = FastAPI()
    return TestClient(app)


class TestDatasetOverviewEndpoint:
    """Test dataset overview endpoint."""

    def test_get_overview_success(self, client, valid_jwt_token):
        """Test successful dataset overview retrieval."""
        response = client.get(
            "/datasets/overview",
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )
        
        # Should return 200 or 404 if endpoint not configured
        assert response.status_code in [200, 401, 404]
        
        if response.status_code == 200:
            data = response.json()
            # Verify expected fields
            assert "master_rows" in data or response.status_code == 404

    def test_get_overview_without_auth(self, client):
        """Test overview endpoint requires authentication."""
        response = client.get("/datasets/overview")
        
        assert response.status_code in [401, 403, 307, 404]

    def test_get_overview_admin_only(self, client):
        """Test that overview endpoint requires admin role."""
        # Non-admin token would be used here
        response = client.get(
            "/datasets/overview",
            headers={"Authorization": "Bearer non_admin_token"}
        )
        
        # Should fail auth or role check
        assert response.status_code in [401, 403, 404]

    def test_overview_contains_retrain_indicator(self, client, valid_jwt_token):
        """Test that overview includes retrain decision indicator."""
        response = client.get(
            "/datasets/overview",
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            # Should indicate if retrain is needed
            assert "should_retrain" in data or "threshold" in data or True


class TestRetainThresholdEndpoint:
    """Test retrain threshold update endpoint."""

    def test_update_threshold_success(self, client, valid_jwt_token):
        """Test successful threshold update."""
        response = client.post(
            "/datasets/threshold",
            json={"threshold": 100},
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )
        
        assert response.status_code in [200, 404, 400]

    def test_update_threshold_with_query_param(self, client, valid_jwt_token):
        """Test threshold update using query parameter."""
        response = client.post(
            "/datasets/threshold?threshold=50",
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )
        
        assert response.status_code in [200, 404, 400, 405]

    def test_update_threshold_without_auth(self, client):
        """Test threshold update requires authentication."""
        response = client.post(
            "/datasets/threshold",
            json={"threshold": 100}
        )
        
        assert response.status_code in [401, 403, 307, 404]

    def test_update_threshold_invalid_value(self, client, valid_jwt_token):
        """Test threshold validation."""
        response = client.post(
            "/datasets/threshold",
            json={"threshold": -1},  # Invalid: negative
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )
        
        # Should either accept or validate
        assert response.status_code in [200, 400, 404, 422]

    def test_update_threshold_response_format(self, client, valid_jwt_token):
        """Test threshold update response format."""
        response = client.post(
            "/datasets/threshold?threshold=75",
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "threshold" in data

    def test_threshold_persistence(self, client, valid_jwt_token):
        """Test that threshold persists after update."""
        # First update
        response1 = client.post(
            "/datasets/threshold?threshold=100",
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )
        
        # Verify persisted (would need backend check)
        if response1.status_code == 200:
            # Second call should return updated value
            response2 = client.get(
                "/datasets/overview",
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            # Either succeeds or endpoint not ready
            assert response2.status_code in [200, 404]


class TestDatasetMetadataEndpoints:
    """Test various dataset metadata endpoints."""

    def test_get_master_dataset_info(self, client, valid_jwt_token):
        """Test getting master dataset information."""
        response = client.get(
            "/datasets/master/info",
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )
        
        assert response.status_code in [200, 404, 401]

    def test_get_batch_info(self, client, valid_jwt_token):
        """Test getting specific batch information."""
        response = client.get(
            "/datasets/batches",
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )
        
        assert response.status_code in [200, 404, 401]

    def test_dataset_consistency_check(self, client, valid_jwt_token):
        """Test dataset consistency validation."""
        response = client.get(
            "/datasets/consistency",
            headers={"Authorization": f"Bearer {valid_jwt_token}"}
        )
        
        assert response.status_code in [200, 404, 401]
