"""
Unit tests for security module.

Tests the actual functions from api/gateway_api/services/security.py.
"""
import sys
from pathlib import Path

import pytest
from passlib.context import CryptContext
from jose import JWTError, jwt
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "api" / "gateway_api"))


class TestPasswordHashing:
    """Test password hashing via project's security module."""

    def test_verify_password_with_correct_password(self):
        """Test verify_password returns True for matching password."""
        from services.security import pwd_context, verify_password

        hashed = pwd_context.hash("testpassword123")
        assert verify_password("testpassword123", hashed) is True

    def test_verify_password_with_incorrect_password(self):
        """Test verify_password returns False for wrong password."""
        from services.security import verify_password, pwd_context

        hashed = pwd_context.hash("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_password_hash_consistency(self):
        """Test same password produces different hashes (bcrypt salting)."""
        from services.security import pwd_context

        password = "testpassword123"
        hash1 = pwd_context.hash(password)
        hash2 = pwd_context.hash(password)

        assert hash1 != hash2
        assert pwd_context.verify(password, hash1)
        assert pwd_context.verify(password, hash2)


class TestJWTTokenGeneration:
    """Test JWT token via create_access_token from security module."""

    def test_create_token_returns_valid_jwt(self):
        """Test create_access_token returns valid JWT string."""
        from services.security import create_access_token

        token = create_access_token({"sub": "testuser", "role": "user"})
        assert isinstance(token, str)
        assert len(token.split(".")) == 3

    def test_decode_valid_token(self):
        """Test decoding a valid token returns correct claims."""
        from services.security import create_access_token
        from core.config import SECRET_KEY, ALGORITHM

        token = create_access_token({"sub": "testuser", "role": "user"})
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        assert payload["sub"] == "testuser"
        assert payload["role"] == "user"
        assert "exp" in payload

    def test_decode_token_with_wrong_secret_raises_error(self):
        """Test decoding with wrong secret key raises JWTError."""
        from services.security import create_access_token

        token = create_access_token({"sub": "testuser", "role": "user"})

        with pytest.raises(JWTError):
            jwt.decode(token, "wrong-secret-key", algorithms=["HS256"])

    def test_token_contains_expiration(self):
        """Test token has valid expiration claim."""
        from services.security import create_access_token
        from core.config import SECRET_KEY, ALGORITHM
        from datetime import datetime

        token = create_access_token({"sub": "testuser", "role": "user"})
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        assert "exp" in decoded
        assert decoded["exp"] > datetime.utcnow().timestamp()


class TestCredentialValidation:
    """Test credential validation via authenticate_user."""

    def test_authenticate_valid_admin(self):
        """Test authenticating with valid admin credentials."""
        from services.security import authenticate_user

        with patch("services.security._db_configured", return_value=False):
            user = authenticate_user("admin", "admin")
            assert user is not None
            assert user["role"] == "admin"

    def test_authenticate_invalid_credentials(self):
        """Test authenticating with invalid credentials returns None."""
        from services.security import authenticate_user

        with patch("services.security._db_configured", return_value=False):
            user = authenticate_user("admin", "wrongpassword")
            assert user is None

    def test_authenticate_nonexistent_user(self):
        """Test authenticating nonexistent user returns None."""
        from services.security import authenticate_user

        with patch("services.security._db_configured", return_value=False):
            user = authenticate_user("nonexistent", "password")
            assert user is None

    def test_token_structure_has_three_parts(self):
        """Test JWT token has standard three-part structure."""
        from services.security import create_access_token

        token = create_access_token({"sub": "user", "role": "user"})
        parts = token.split(".")
        assert len(parts) == 3


class TestSecurityConfig:
    """Test security configuration values."""

    def test_secret_key_not_empty(self):
        """Test SECRET_KEY is configured and non-empty."""
        from core.config import SECRET_KEY

        assert SECRET_KEY is not None
        assert len(SECRET_KEY) > 0

    def test_algorithm_is_secure(self):
        """Test ALGORITHM is a recognized secure algorithm."""
        from core.config import ALGORITHM

        secure_algorithms = {"HS256", "RS256", "ES256"}
        assert ALGORITHM in secure_algorithms

    def test_token_expire_minutes_is_positive(self):
        """Test ACCESS_TOKEN_EXPIRE_MINUTES is positive."""
        from core.config import ACCESS_TOKEN_EXPIRE_MINUTES

        assert ACCESS_TOKEN_EXPIRE_MINUTES > 0

    def test_different_secrets_produce_different_tokens(self):
        """Test tokens signed with different keys differ."""
        from datetime import datetime, timedelta

        payload = {"sub": "user", "exp": datetime.utcnow() + timedelta(hours=1)}
        token1 = jwt.encode(payload, "secret-key-1", algorithm="HS256")
        token2 = jwt.encode(payload, "secret-key-2", algorithm="HS256")

        assert token1 != token2
