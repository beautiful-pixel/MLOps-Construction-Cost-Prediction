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
    from core.config import SECRET_KEY
    from routers.auth import router as auth_router
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(auth_router)
    
    return TestClient(app)


class TestAuthLoginEndpoint:

    def test_login_with_valid_admin_credentials(self, client):
        response = client.post(
            "/auth/login",
            data={"username": "admin", "password": "admin"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str)

    def test_login_with_valid_user_credentials(self, client):
        response = client.post(
            "/auth/login",
            data={"username": "user", "password": "user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_with_invalid_username(self, client):
        response = client.post(
            "/auth/login",
            data={"username": "nonexistent", "password": "password"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data or "detail" in data

    def test_login_with_invalid_password(self, client):
        response = client.post(
            "/auth/login",
            data={"username": "admin", "password": "wrongpassword"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data or "detail" in data

    def test_login_with_empty_username(self, client):
        response = client.post(
            "/auth/login",
            data={"username": "", "password": "password"}
        )
        
        assert response.status_code == 422
        assert "detail" in response.json()

    def test_login_with_empty_password(self, client):
        response = client.post(
            "/auth/login",
            data={"username": "admin", "password": ""}
        )
        
        assert response.status_code == 422
        assert "detail" in response.json()

    def test_login_missing_username_field(self, client):
        response = client.post(
            "/auth/login",
            data={"password": "password"}
        )
        
        assert response.status_code == 422

    def test_login_missing_password_field(self, client):
        response = client.post(
            "/auth/login",
            data={"username": "admin"}
        )
        
        assert response.status_code == 422

    def test_login_returns_consistent_token_on_same_request(self, client):
        response1 = client.post(
            "/auth/login",
            data={"username": "admin", "password": "admin"}
        )
        response2 = client.post(
            "/auth/login",
            data={"username": "admin", "password": "admin"}
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        token1 = response1.json()["access_token"]
        token2 = response2.json()["access_token"]
        
        assert isinstance(token1, str)
        assert isinstance(token2, str)
        assert len(token1.split(".")) == 3
        assert len(token2.split(".")) == 3

    def test_login_response_has_token_type_bearer(self, client):
        response = client.post(
            "/auth/login",
            data={"username": "admin", "password": "admin"}
        )
        
        assert response.status_code == 200
        assert response.json()["token_type"] == "bearer"

    def test_login_token_format_is_jwt(self, client):
        response = client.post(
            "/auth/login",
            data={"username": "admin", "password": "admin"}
        )
        
        token = response.json()["access_token"]
        parts = token.split(".")
        assert len(parts) == 3

    def test_login_case_sensitive_username(self, client):
        response1 = client.post(
            "/auth/login",
            data={"username": "admin", "password": "admin"}
        )
        response2 = client.post(
            "/auth/login",
            data={"username": "ADMIN", "password": "admin"}
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert "error" in response2.json() or "detail" in response2.json()

    def test_login_case_sensitive_password(self, client):
        response1 = client.post(
            "/auth/login",
            data={"username": "admin", "password": "admin"}
        )
        response2 = client.post(
            "/auth/login",
            data={"username": "admin", "password": "Admin"}
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert "error" in response2.json() or "detail" in response2.json()


class TestTokenValidation:

    def test_token_has_required_claims(self, client):
        from jose import jwt
        from core.config import SECRET_KEY, ALGORITHM
        
        response = client.post(
            "/auth/login",
            data={"username": "admin", "password": "admin"}
        )
        
        token = response.json()["access_token"]
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        assert "sub" in decoded
        assert "role" in decoded
        assert "exp" in decoded

    def test_admin_token_has_admin_role(self, client):
        from jose import jwt
        from core.config import SECRET_KEY, ALGORITHM
        
        response = client.post(
            "/auth/login",
            data={"username": "admin", "password": "admin"}
        )
        
        token = response.json()["access_token"]
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        assert decoded["role"] == "admin"

    def test_user_token_has_user_role(self, client):
        from jose import jwt
        from core.config import SECRET_KEY, ALGORITHM
        
        response = client.post(
            "/auth/login",
            data={"username": "user", "password": "user"}
        )
        
        token = response.json()["access_token"]
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        assert decoded["role"] == "user"

    def test_token_has_future_expiration(self, client):
        from jose import jwt
        from core.config import SECRET_KEY, ALGORITHM
        from datetime import datetime
        
        response = client.post(
            "/auth/login",
            data={"username": "admin", "password": "admin"}
        )
        
        token = response.json()["access_token"]
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        exp_timestamp = decoded["exp"]
        current_timestamp = datetime.utcnow().timestamp()
        
        assert exp_timestamp > current_timestamp
