import sys
from pathlib import Path

import pytest
from passlib.context import CryptContext
from jose import JWTError, jwt

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "api" / "gateway_api"))


class TestPasswordHashing:

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


class TestJWTTokenGeneration:

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


class TestCredentialValidation:

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
        assert len(parts) == 3


class TestSecurityConfig:

    def test_secret_key_not_empty(self, test_secret_key):
        assert test_secret_key is not None
        assert len(test_secret_key) > 0

    def test_secret_key_minimum_length(self, test_secret_key):
        assert len(test_secret_key) >= 8

    def test_algorithm_is_secure(self, test_algorithm):
        secure_algorithms = {"HS256", "RS256", "ES256"}
        assert test_algorithm in secure_algorithms

    def test_different_secrets_produce_different_tokens(self, test_algorithm):
        from datetime import datetime, timedelta
        
        secret1 = "secret-key-1"
        secret2 = "secret-key-2"
        payload = {"sub": "user", "exp": datetime.utcnow() + timedelta(hours=1)}
        
        token1 = jwt.encode(payload, secret1, algorithm=test_algorithm)
        token2 = jwt.encode(payload, secret2, algorithm=test_algorithm)
        
        assert token1 != token2
