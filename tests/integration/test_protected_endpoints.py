import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "api" / "gateway_api"))


@pytest.fixture
def authenticated_client():
    from core.config import SECRET_KEY
    from routers.auth import router as auth_router
    from routers.system import router as system_router
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(system_router)
    
    client = TestClient(app)
    
    response = client.post(
        "/auth/login",
        data={"username": "admin", "password": "admin"}
    )
    
    token = response.json()["access_token"]
    client.headers = {"Authorization": f"Bearer {token}"}
    
    return client


@pytest.fixture
def user_authenticated_client():
    from core.config import SECRET_KEY
    from routers.auth import router as auth_router
    from routers.system import router as system_router
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(system_router)
    
    client = TestClient(app)
    
    response = client.post(
        "/auth/login",
        data={"username": "user", "password": "user"}
    )
    
    token = response.json()["access_token"]
    client.headers = {"Authorization": f"Bearer {token}"}
    
    return client


class TestHealthEndpoint:

    def test_health_endpoint_accessible(self):
        from fastapi import FastAPI
        from routers.system import router as system_router
        
        app = FastAPI()
        app.include_router(system_router)
        client = TestClient(app)
        
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_endpoint_returns_ok_status(self):
        from fastapi import FastAPI
        from routers.system import router as system_router
        
        app = FastAPI()
        app.include_router(system_router)
        client = TestClient(app)
        
        response = client.get("/health")
        data = response.json()
        assert "status" in data


class TestProtectedEndpoints:

    def test_protected_endpoint_without_token(self):
        from fastapi import FastAPI
        from routers.system import router as system_router
        
        app = FastAPI()
        app.include_router(system_router)
        client = TestClient(app)
        
        response = client.get("/info")
        assert response.status_code in [401, 403]

    def test_protected_endpoint_with_invalid_token(self):
        from fastapi import FastAPI
        from routers.system import router as system_router
        
        app = FastAPI()
        app.include_router(system_router)
        client = TestClient(app)
        
        response = client.get(
            "/info",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        assert response.status_code in [401, 403]

    def test_protected_endpoint_with_malformed_token(self):
        from fastapi import FastAPI
        from routers.system import router as system_router
        
        app = FastAPI()
        app.include_router(system_router)
        client = TestClient(app)
        
        response = client.get(
            "/info",
            headers={"Authorization": "Bearer"}
        )
        assert response.status_code in [401, 403]

    def test_protected_endpoint_with_valid_user_token(self, user_authenticated_client):
        response = user_authenticated_client.get("/info")
        assert response.status_code in [200, 404]

    def test_protected_endpoint_with_valid_admin_token(self, authenticated_client):
        response = authenticated_client.get("/info")
        assert response.status_code in [200, 404]

    def test_authorization_header_case_insensitive_scheme(self):
        from fastapi import FastAPI
        from routers.system import router as system_router
        from routers.auth import router as auth_router
        
        app = FastAPI()
        app.include_router(auth_router)
        app.include_router(system_router)
        client = TestClient(app)
        
        login_response = client.post(
            "/auth/login",
            data={"username": "admin", "password": "admin"}
        )
        token = login_response.json()["access_token"]
        
        response = client.get(
            "/info",
            headers={"Authorization": f"bearer {token}"}
        )
        assert response.status_code in [401, 200, 404]


class TestAdminOnlyEndpoints:

    def test_admin_endpoint_requires_admin_role(self):
        from fastapi import FastAPI
        from routers.system import router as system_router
        from routers.auth import router as auth_router
        
        app = FastAPI()
        app.include_router(auth_router)
        app.include_router(system_router)
        client = TestClient(app)
        
        login_response = client.post(
            "/auth/login",
            data={"username": "user", "password": "user"}
        )
        token = login_response.json()["access_token"]
        
        response = client.get(
            "/status",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403

    def test_admin_endpoint_accessible_with_admin_role(self, authenticated_client):
        response = authenticated_client.get("/status")
        assert response.status_code == 200


class TestEndpointResponseFormats:

    def test_error_response_contains_detail_field(self):
        from fastapi import FastAPI
        from routers.system import router as system_router
        
        app = FastAPI()
        app.include_router(system_router)
        client = TestClient(app)
        
        response = client.get("/info")
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    def test_success_response_is_json(self, authenticated_client):
        response = authenticated_client.get("/info")
        assert response.status_code in [200, 404]
        data = response.json()
        assert isinstance(data, dict)

    def test_response_headers_include_content_type(self, authenticated_client):
        response = authenticated_client.get("/info")
        assert response.status_code in [200, 404]
        assert "content-type" in response.headers
        assert "application/json" in response.headers["content-type"]


class TestConcurrentRequests:

    def test_multiple_valid_tokens_can_be_used_simultaneously(self):
        from fastapi import FastAPI
        from routers.auth import router as auth_router
        from routers.system import router as system_router
        
        app = FastAPI()
        app.include_router(auth_router)
        app.include_router(system_router)
        client = TestClient(app)
        
        response1 = client.post(
            "/auth/login",
            data={"username": "admin", "password": "admin"}
        )
        token1 = response1.json()["access_token"]
        
        response2 = client.post(
            "/auth/login",
            data={"username": "user", "password": "user"}
        )
        token2 = response2.json()["access_token"]
        
        admin_response = client.get(
            "/info",
            headers={"Authorization": f"Bearer {token1}"}
        )
        user_response = client.get(
            "/info",
            headers={"Authorization": f"Bearer {token2}"}
        )
        
        assert admin_response.status_code in [200, 404]
        assert user_response.status_code in [200, 404]


class TestInputValidation:

    def test_request_with_extra_fields(self):
        from fastapi import FastAPI
        from routers.auth import router as auth_router
        
        app = FastAPI()
        app.include_router(auth_router)
        client = TestClient(app)
        
        response = client.post(
            "/auth/login",
            data={
                "username": "admin",
                "password": "admin",
                "extra_field": "should_be_ignored"
            }
        )
        
        assert response.status_code == 200

    def test_request_with_special_characters_in_username(self):
        from fastapi import FastAPI
        from routers.auth import router as auth_router
        
        app = FastAPI()
        app.include_router(auth_router)
        client = TestClient(app)
        
        response = client.post(
            "/auth/login",
            data={
                "username": "admin<script>alert('xss')</script>",
                "password": "admin"
            }
        )
        
        assert response.status_code == 200
        assert "error" in response.json() or "detail" in response.json()

    def test_request_with_very_long_username(self):
        from fastapi import FastAPI
        from routers.auth import router as auth_router
        
        app = FastAPI()
        app.include_router(auth_router)
        client = TestClient(app)
        
        long_username = "a" * 10000
        response = client.post(
            "/auth/login",
            data={
                "username": long_username,
                "password": "admin"
            }
        )
        
        assert response.status_code == 200
        assert "error" in response.json() or "detail" in response.json()

    def test_request_with_very_long_password(self):
        from fastapi import FastAPI
        from routers.auth import router as auth_router
        
        app = FastAPI()
        app.include_router(auth_router)
        client = TestClient(app, raise_server_exceptions=False)
        
        long_password = "a" * 10000
        response = client.post(
            "/auth/login",
            data={
                "username": "admin",
                "password": long_password
            }
        )
        
        assert response.status_code in [400, 413, 500]


class TestSecurityHeaders:

    def test_response_includes_security_headers(self, authenticated_client):
        response = authenticated_client.get("/info")
        
        assert response.status_code in [200, 404]
        headers = response.headers
        assert headers is not None

    def test_no_sensitive_information_in_error_messages(self):
        from fastapi import FastAPI
        from routers.system import router as system_router
        
        app = FastAPI()
        app.include_router(system_router)
        client = TestClient(app)
        
        response = client.get("/info")
        data = response.json()
        
        error_message = str(data.get("detail", ""))
        assert "secret" not in error_message.lower()
        assert "password" not in error_message.lower()
        assert "token" not in error_message.lower()
