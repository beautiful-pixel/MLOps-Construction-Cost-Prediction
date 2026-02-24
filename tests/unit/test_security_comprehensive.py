"""
Comprehensive security and authentication tests.

Tests the ACTUAL security functions from api/gateway_api/services/security.py.
"""
import sys
from pathlib import Path
import pytest
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "api" / "gateway_api"))


class TestPasswordHashing:
    """Test password hashing using the project's security module."""

    def test_verify_password_correct(self):
        """Test verify_password returns True for correct password."""
        from services.security import pwd_context, verify_password

        hashed = pwd_context.hash("testpassword")
        assert verify_password("testpassword", hashed) is True

    def test_verify_password_incorrect(self):
        """Test verify_password returns False for wrong password."""
        from services.security import pwd_context, verify_password

        hashed = pwd_context.hash("testpassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_password_hash_uses_bcrypt(self):
        """Test that password hashing uses bcrypt scheme."""
        from services.security import pwd_context

        hashed = pwd_context.hash("test")
        # bcrypt hashes start with $2b$
        assert hashed.startswith("$2b$")

    def test_same_password_produces_different_hashes(self):
        """Test bcrypt salting produces unique hashes."""
        from services.security import pwd_context

        hash1 = pwd_context.hash("samepassword")
        hash2 = pwd_context.hash("samepassword")
        assert hash1 != hash2
        assert pwd_context.verify("samepassword", hash1)
        assert pwd_context.verify("samepassword", hash2)


class TestJWTTokenGeneration:
    """Test JWT token creation using the project's create_access_token."""

    def test_create_access_token_returns_string(self):
        """Test create_access_token returns a JWT string."""
        from services.security import create_access_token

        token = create_access_token({"sub": "testuser", "role": "user"})
        assert isinstance(token, str)
        assert len(token.split(".")) == 3  # JWT has 3 parts

    def test_token_contains_subject_claim(self):
        """Test token contains the 'sub' claim."""
        from services.security import create_access_token
        from core.config import SECRET_KEY, ALGORITHM

        token = create_access_token({"sub": "testuser", "role": "user"})
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert decoded["sub"] == "testuser"

    def test_token_contains_role_claim(self):
        """Test token contains the 'role' claim."""
        from services.security import create_access_token
        from core.config import SECRET_KEY, ALGORITHM

        token = create_access_token({"sub": "admin_user", "role": "admin"})
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert decoded["role"] == "admin"

    def test_token_has_expiration(self):
        """Test token has an expiration time in the future."""
        from services.security import create_access_token
        from core.config import SECRET_KEY, ALGORITHM

        token = create_access_token({"sub": "user", "role": "user"})
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        assert "exp" in decoded
        assert decoded["exp"] > datetime.utcnow().timestamp()

    def test_token_expiration_uses_configured_minutes(self):
        """Test token expiration matches ACCESS_TOKEN_EXPIRE_MINUTES."""
        from services.security import create_access_token
        from core.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

        before = datetime.utcnow()
        token = create_access_token({"sub": "user", "role": "user"})
        after = datetime.utcnow()

        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_time = datetime.utcfromtimestamp(decoded["exp"])

        # Token should expire approximately ACCESS_TOKEN_EXPIRE_MINUTES from now
        expected_min = before + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES) - timedelta(seconds=2)
        expected_max = after + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES) + timedelta(seconds=2)
        assert expected_min <= exp_time <= expected_max

    def test_token_tampering_detected(self):
        """Test that tampered tokens are rejected."""
        from services.security import create_access_token
        from core.config import SECRET_KEY, ALGORITHM

        token = create_access_token({"sub": "user", "role": "user"})
        parts = token.split(".")
        tampered = parts[0] + "." + parts[1] + ".tampered_signature"

        with pytest.raises(JWTError):
            jwt.decode(tampered, SECRET_KEY, algorithms=[ALGORITHM])

    def test_token_with_wrong_secret_rejected(self):
        """Test token decoded with wrong secret raises error."""
        from services.security import create_access_token

        token = create_access_token({"sub": "user", "role": "user"})

        with pytest.raises(JWTError):
            jwt.decode(token, "wrong-secret-key", algorithms=["HS256"])


class TestAuthenticateUser:
    """Test the authenticate_user function against fake_users_db."""

    @patch.dict("os.environ", {}, clear=False)
    def test_authenticate_valid_admin(self):
        """Test authenticating with valid admin credentials."""
        from services.security import authenticate_user

        # Clear DB env vars to force fake_users_db
        with patch("services.security._db_configured", return_value=False):
            user = authenticate_user("admin", "admin")
            assert user is not None
            assert user["username"] == "admin"
            assert user["role"] == "admin"

    @patch.dict("os.environ", {}, clear=False)
    def test_authenticate_valid_user(self):
        """Test authenticating with valid user credentials."""
        from services.security import authenticate_user

        with patch("services.security._db_configured", return_value=False):
            user = authenticate_user("user", "user")
            assert user is not None
            assert user["username"] == "user"
            assert user["role"] == "user"

    @patch.dict("os.environ", {}, clear=False)
    def test_authenticate_wrong_password_returns_none(self):
        """Test authenticating with wrong password returns None."""
        from services.security import authenticate_user

        with patch("services.security._db_configured", return_value=False):
            user = authenticate_user("admin", "wrongpassword")
            assert user is None

    @patch.dict("os.environ", {}, clear=False)
    def test_authenticate_nonexistent_user_returns_none(self):
        """Test authenticating nonexistent user returns None."""
        from services.security import authenticate_user

        with patch("services.security._db_configured", return_value=False):
            user = authenticate_user("nonexistent", "password")
            assert user is None


class TestGetCurrentUser:
    """Test the get_current_user token decoding function."""

    def test_valid_token_returns_user_dict(self):
        """Test valid token is decoded to user dict."""
        from services.security import create_access_token, get_current_user

        token = create_access_token({"sub": "testuser", "role": "user"})
        user = get_current_user(token)

        assert user["username"] == "testuser"
        assert user["role"] == "user"

    def test_expired_token_raises_401(self):
        """Test expired token raises HTTPException."""
        from services.security import get_current_user
        from core.config import SECRET_KEY, ALGORITHM
        from fastapi import HTTPException

        payload = {
            "sub": "testuser",
            "role": "user",
            "exp": datetime.utcnow() - timedelta(hours=1),
        }
        expired_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(expired_token)
        assert exc_info.value.status_code == 401

    def test_invalid_token_raises_401(self):
        """Test invalid token raises HTTPException."""
        from services.security import get_current_user
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            get_current_user("invalid.token.here")
        assert exc_info.value.status_code == 401

    def test_token_without_sub_raises_401(self):
        """Test token missing 'sub' claim raises HTTPException."""
        from services.security import get_current_user
        from core.config import SECRET_KEY, ALGORITHM
        from fastapi import HTTPException

        payload = {
            "role": "user",
            "exp": datetime.utcnow() + timedelta(hours=1),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token)
        assert exc_info.value.status_code == 401


class TestRoleAuthorization:
    """Test require_user and require_admin role checks."""

    def test_require_user_accepts_user_role(self):
        """Test require_user allows user role."""
        from services.security import require_user

        user = {"username": "test", "role": "user"}
        result = require_user(user)
        assert result == user

    def test_require_user_accepts_admin_role(self):
        """Test require_user allows admin role."""
        from services.security import require_user

        user = {"username": "admin", "role": "admin"}
        result = require_user(user)
        assert result == user

    def test_require_user_rejects_invalid_role(self):
        """Test require_user rejects unknown roles."""
        from services.security import require_user
        from fastapi import HTTPException

        user = {"username": "test", "role": "superuser"}
        with pytest.raises(HTTPException) as exc_info:
            require_user(user)
        assert exc_info.value.status_code == 403

    def test_require_admin_accepts_admin(self):
        """Test require_admin allows admin role."""
        from services.security import require_admin

        user = {"username": "admin", "role": "admin"}
        result = require_admin(user)
        assert result == user

    def test_require_admin_rejects_user_role(self):
        """Test require_admin rejects user role."""
        from services.security import require_admin
        from fastapi import HTTPException

        user = {"username": "test", "role": "user"}
        with pytest.raises(HTTPException) as exc_info:
            require_admin(user)
        assert exc_info.value.status_code == 403
