import sys
from pathlib import Path
from datetime import datetime, timedelta

import pytest
from passlib.context import CryptContext
from jose import jwt

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "api" / "gateway_api"))

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
