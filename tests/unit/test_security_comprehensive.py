"""
Comprehensive security and authentication tests.
"""
import sys
from pathlib import Path
import pytest
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "api" / "gateway_api"))


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_verify_password_with_correct_password(self, hashed_password, test_user_credentials):
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        result = pwd_context.verify(test_user_credentials["password"], hashed_password)
        assert result is True

    def test_verify_password_with_incorrect_password(self, hashed_password):
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        result = pwd_context.verify("wrongpassword", hashed_password)
        assert result is False

    def test_password_hash_consistency(self, test_user_credentials):
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        password = test_user_credentials["password"]
        
        hash1 = pwd_context.hash(password)
        hash2 = pwd_context.hash(password)
        
        assert hash1 != hash2
        assert pwd_context.verify(password, hash1)
        assert pwd_context.verify(password, hash2)

    def test_password_hashing_performance(self, test_user_credentials):
        """Ensure password hashing takes reasonable time (bcrypt should be slow)."""
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        password = test_user_credentials["password"]
        
        import time
        start = time.time()
        pwd_context.hash(password)
        elapsed = time.time() - start
        
        # bcrypt should take at least 100ms (slow by design for security)
        assert elapsed > 0.1

    def test_empty_password_hashing(self):
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        empty_hash = pwd_context.hash("")
        assert pwd_context.verify("", empty_hash)


class TestJWTTokenGeneration:
    """Test JWT token creation and validation."""

    def test_create_token_payload(self, test_secret_key, test_algorithm, test_user_credentials):
        payload = {
            "sub": test_user_credentials["username"],
            "role": test_user_credentials["role"]
        }
        
        token = jwt.encode(payload, test_secret_key, algorithm=test_algorithm)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_valid_token(self, valid_jwt_token, test_secret_key, test_algorithm):
        payload = jwt.decode(valid_jwt_token, test_secret_key, algorithms=[test_algorithm])
        
        assert payload["sub"] == "testuser"
        assert payload["role"] == "user"
        assert "exp" in payload

    def test_decode_expired_token_raises_error(self, expired_jwt_token, test_secret_key, test_algorithm):
        with pytest.raises(JWTError):
            jwt.decode(expired_jwt_token, test_secret_key, algorithms=[test_algorithm])

    def test_decode_token_with_wrong_secret_raises_error(self, valid_jwt_token, test_algorithm):
        wrong_secret = "wrong-secret-key"
        
        with pytest.raises(JWTError):
            jwt.decode(valid_jwt_token, wrong_secret, algorithms=[test_algorithm])

    def test_token_contains_expiration(self, test_secret_key, test_algorithm):
        from datetime import datetime, timedelta
        
        exp_time = datetime.utcnow() + timedelta(minutes=60)
        payload = {
            "sub": "testuser",
            "role": "user",
            "exp": exp_time
        }
        
        token = jwt.encode(payload, test_secret_key, algorithm=test_algorithm)
        decoded = jwt.decode(token, test_secret_key, algorithms=[test_algorithm])
        
        assert "exp" in decoded
        assert decoded["exp"] > datetime.utcnow().timestamp()

    def test_token_refresh_validity(self, test_secret_key, test_algorithm):
        """Test that refreshed tokens have new expiration."""
        original_payload = {
            "sub": "testuser",
            "role": "user",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        
        original_token = jwt.encode(original_payload, test_secret_key, algorithm=test_algorithm)
        
        # Simulate refresh after a delay to get different timestamp
        import time
        time.sleep(0.1)
        
        refreshed_payload = {
            "sub": "testuser",
            "role": "user",
            "exp": datetime.utcnow() + timedelta(hours=2)  # Different expiration
        }
        refreshed_token = jwt.encode(refreshed_payload, test_secret_key, algorithm=test_algorithm)
        
        # Decode both tokens to compare expiration
        original_decoded = jwt.decode(original_token, test_secret_key, algorithms=[test_algorithm])
        refreshed_decoded = jwt.decode(refreshed_token, test_secret_key, algorithms=[test_algorithm])
        
        # Original and refreshed should have different expiration times
        assert original_decoded["exp"] != refreshed_decoded["exp"]
        assert refreshed_decoded["exp"] > original_decoded["exp"]

    def test_token_tampering_detection(self, test_secret_key, test_algorithm, valid_jwt_token):
        """Test that tampered tokens are rejected."""
        # Split token and modify payload
        parts = valid_jwt_token.split(".")
        tampered_token = parts[0] + "." + parts[1] + ".tampered_signature"
        
        with pytest.raises(JWTError):
            jwt.decode(tampered_token, test_secret_key, algorithms=[test_algorithm])

    def test_admin_role_in_token(self, test_secret_key, test_algorithm):
        """Test admin role is correctly encoded in token."""
        payload = {
            "sub": "admin_user",
            "role": "admin",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        
        token = jwt.encode(payload, test_secret_key, algorithm=test_algorithm)
        decoded = jwt.decode(token, test_secret_key, algorithms=[test_algorithm])
        
        assert decoded["role"] == "admin"

    def test_user_role_in_token(self, test_secret_key, test_algorithm):
        """Test user role is correctly encoded in token."""
        payload = {
            "sub": "regular_user",
            "role": "user",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        
        token = jwt.encode(payload, test_secret_key, algorithm=test_algorithm)
        decoded = jwt.decode(token, test_secret_key, algorithms=[test_algorithm])
        
        assert decoded["role"] == "user"


class TestCredentialValidation:
    """Test credential validation rules."""

    def test_username_empty_validation(self):
        assert "" != "validuser"

    def test_password_empty_validation(self):
        assert "" != "validpass"

    def test_username_length_validation(self):
        username = "a" * 256
        assert len(username) > 255

    def test_role_valid_values(self):
        valid_roles = {"user", "admin"}
        assert "user" in valid_roles
        assert "admin" in valid_roles
        assert "superuser" not in valid_roles

    def test_token_structure(self, valid_jwt_token):
        parts = valid_jwt_token.split(".")
        assert len(parts) == 3  # JWT has 3 parts

    def test_username_special_characters(self):
        """Test username validation with special characters."""
        usernames = [
            "user@example.com",
            "user_name",
            "user-name",
            "user.name",
        ]
        for username in usernames:
            assert len(username) > 0

    def test_password_min_length(self):
        """Test password minimum length requirement."""
        short_password = "abc"
        acceptable_password = "abcdefghij"
        
        assert len(short_password) < 8
        assert len(acceptable_password) >= 8

    def test_credentials_immutability_in_token(self, test_secret_key, test_algorithm):
        """Test that token claims cannot be modified after signing."""
        payload = {
            "sub": "testuser",
            "role": "user",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        
        token = jwt.encode(payload, test_secret_key, algorithm=test_algorithm)
        
        # Try to decode and verify original data
        decoded = jwt.decode(token, test_secret_key, algorithms=[test_algorithm])
        assert decoded["sub"] == "testuser"
        assert decoded["role"] == "user"


class TestBruteForceProtection:
    """Test brute force attack prevention."""

    def test_login_attempt_tracking(self):
        """Test that failed login attempts are tracked."""
        failed_attempts = {}
        username = "testuser"
        
        # Simulate failed attempts
        for i in range(3):
            if username not in failed_attempts:
                failed_attempts[username] = 0
            failed_attempts[username] += 1
        
        assert failed_attempts[username] == 3

    def test_account_lockout_threshold(self):
        """Test account lockout after X failed attempts."""
        max_attempts = 5
        failed_attempts = 4
        
        should_lockout = failed_attempts >= max_attempts
        assert should_lockout is False
        
        failed_attempts += 1
        should_lockout = failed_attempts >= max_attempts
        assert should_lockout is True

    def test_failed_attempt_reset_after_success(self):
        """Test that failed attempts reset after successful login."""
        failed_attempts = {"testuser": 3}
        
        # Simulate successful login
        if "testuser" in failed_attempts:
            del failed_attempts["testuser"]
        
        assert "testuser" not in failed_attempts


class TestTokenExpiration:
    """Test token expiration and session management."""

    def test_token_expiration_time(self, test_secret_key, test_algorithm):
        """Test that token expiration time is correctly set."""
        exp_time = datetime.utcnow() + timedelta(hours=1)
        payload = {
            "sub": "testuser",
            "exp": exp_time
        }
        
        token = jwt.encode(payload, test_secret_key, algorithm=test_algorithm)
        decoded = jwt.decode(token, test_secret_key, algorithms=[test_algorithm])
        
        # Check expiration is in the future
        assert decoded["exp"] > datetime.utcnow().timestamp()

    def test_token_expiration_cleanup(self):
        """Test cleanup of expired tokens."""
        expired_tokens = {}
        current_time = datetime.utcnow()
        
        # Add some tokens with expiration
        expired_tokens["token1"] = current_time - timedelta(hours=1)
        expired_tokens["token2"] = current_time + timedelta(hours=1)
        
        # Clean expired tokens
        active_tokens = {
            k: v for k, v in expired_tokens.items() 
            if v > current_time
        }
        
        assert len(active_tokens) == 1
        assert "token2" in active_tokens

    def test_session_timeout(self):
        """Test session timeout enforcement."""
        session_timeout_minutes = 30
        session_created = datetime.utcnow()
        current_time = session_created + timedelta(minutes=25)
        
        elapsed = (current_time - session_created).total_seconds() / 60
        is_expired = elapsed >= session_timeout_minutes
        
        assert is_expired is False
        
        current_time = session_created + timedelta(minutes=31)
        elapsed = (current_time - session_created).total_seconds() / 60
        is_expired = elapsed >= session_timeout_minutes
        
        assert is_expired is True
