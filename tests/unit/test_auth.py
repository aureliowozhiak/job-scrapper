"""Unit tests for authentication utilities."""
import pytest
import base64
from src.core.auth import (
    verify_password,
    hash_password,
    verify_credentials,
    get_basic_auth_credentials
)


class TestPasswordHashing:
    """Tests for password hashing and verification."""
    
    def test_hash_password(self):
        """Test password hashing."""
        password = "test_password_123"
        hashed = hash_password(password)
        
        assert hashed is not None
        assert hashed != password
        assert hashed.startswith("$2b$")
    
    def test_verify_password_correct(self):
        """Test verifying correct password."""
        password = "test_password_123"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test verifying incorrect password."""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = hash_password(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_verify_password_invalid_hash(self):
        """Test verifying password with invalid hash."""
        result = verify_password("test", "invalid_hash")
        assert result is False
    
    def test_verify_password_empty_string(self):
        """Test verifying empty password."""
        hashed = hash_password("test")
        assert verify_password("", hashed) is False


class TestCredentialVerification:
    """Tests for credential verification."""
    
    def test_verify_credentials_correct(self):
        """Test verifying correct credentials."""
        username = "admin"
        password = "admin123"
        hashed = hash_password(password)
        
        result = verify_credentials(username, password, username, hashed)
        assert result is True
    
    def test_verify_credentials_wrong_username(self):
        """Test verifying with wrong username."""
        username = "admin"
        password = "admin123"
        hashed = hash_password(password)
        
        result = verify_credentials("wrong_user", password, username, hashed)
        assert result is False
    
    def test_verify_credentials_wrong_password(self):
        """Test verifying with wrong password."""
        username = "admin"
        password = "admin123"
        hashed = hash_password(password)
        
        result = verify_credentials(username, "wrong_pass", username, hashed)
        assert result is False
    
    def test_verify_credentials_both_wrong(self):
        """Test verifying with both username and password wrong."""
        username = "admin"
        password = "admin123"
        hashed = hash_password(password)
        
        result = verify_credentials("wrong", "wrong", username, hashed)
        assert result is False


class TestBasicAuthParsing:
    """Tests for HTTP Basic Auth parsing."""
    
    def test_get_basic_auth_credentials_valid(self):
        """Test parsing valid Basic Auth header."""
        username = "admin"
        password = "admin123"
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        header = f"Basic {credentials}"
        
        result = get_basic_auth_credentials(header)
        assert result == (username, password)
    
    def test_get_basic_auth_credentials_none(self):
        """Test parsing None header."""
        result = get_basic_auth_credentials(None)
        assert result is None
    
    def test_get_basic_auth_credentials_empty(self):
        """Test parsing empty header."""
        result = get_basic_auth_credentials("")
        assert result is None
    
    def test_get_basic_auth_credentials_wrong_scheme(self):
        """Test parsing wrong auth scheme."""
        credentials = base64.b64encode(b"admin:admin123").decode()
        header = f"Bearer {credentials}"
        
        result = get_basic_auth_credentials(header)
        assert result is None
    
    def test_get_basic_auth_credentials_invalid_base64(self):
        """Test parsing invalid base64."""
        header = "Basic not_valid_base64!!!"
        
        result = get_basic_auth_credentials(header)
        assert result is None
    
    def test_get_basic_auth_credentials_no_colon(self):
        """Test parsing credentials without colon separator."""
        credentials = base64.b64encode(b"adminadmin123").decode()
        header = f"Basic {credentials}"
        
        result = get_basic_auth_credentials(header)
        assert result is None
    
    def test_get_basic_auth_credentials_password_with_colon(self):
        """Test parsing password containing colon."""
        username = "admin"
        password = "pass:word:123"
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        header = f"Basic {credentials}"
        
        result = get_basic_auth_credentials(header)
        assert result == (username, password)
    
    def test_get_basic_auth_credentials_malformed_header(self):
        """Test parsing malformed header (missing space)."""
        result = get_basic_auth_credentials("BasicTokenHere")
        assert result is None
