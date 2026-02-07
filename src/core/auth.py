"""Authentication utilities for password hashing and verification."""
from passlib.hash import bcrypt
from typing import Optional


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a bcrypt hash.
    
    Args:
        plain_password: The plain text password to verify
        hashed_password: The bcrypt hash to verify against
    
    Returns:
        True if the password matches the hash, False otherwise
    """
    try:
        return bcrypt.verify(plain_password, hashed_password)
    except Exception:
        return False


def hash_password(plain_password: str) -> str:
    """
    Generate a bcrypt hash for a plain text password.
    
    This is a developer utility for generating password hashes.
    
    Args:
        plain_password: The plain text password to hash
    
    Returns:
        The bcrypt hash of the password
    
    Example:
        >>> hash_password("admin123")
        '$2b$12$...'
    """
    return bcrypt.hash(plain_password)


def verify_credentials(username: str, password: str, expected_username: str, expected_password_hash: str) -> bool:
    """
    Verify username and password credentials.
    
    Args:
        username: The username to verify
        password: The password to verify
        expected_username: The expected username
        expected_password_hash: The expected password hash
    
    Returns:
        True if both username and password are correct, False otherwise
    """
    if username != expected_username:
        return False
    
    return verify_password(password, expected_password_hash)


def get_basic_auth_credentials(authorization: Optional[str]) -> Optional[tuple[str, str]]:
    """
    Extract username and password from HTTP Basic Auth header.
    
    Args:
        authorization: The Authorization header value (e.g., "Basic dXNlcjpwYXNz")
    
    Returns:
        A tuple of (username, password) if valid, None otherwise
    """
    if not authorization:
        return None
    
    try:
        import base64
        scheme, credentials = authorization.split(' ', 1)
        if scheme.lower() != 'basic':
            return None
        
        decoded = base64.b64decode(credentials).decode('utf-8')
        username, password = decoded.split(':', 1)
        return username, password
    except Exception:
        return None
