"""Authentication utilities for password hashing and verification."""
import bcrypt
from typing import Optional
import base64


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False


def hash_password(plain_password: str) -> str:
    """Generate a bcrypt hash for a plain text password."""
    hashed = bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')


def verify_credentials(username: str, password: str, expected_username: str, expected_password_hash: str) -> bool:
    """Verify username and password credentials."""
    if username != expected_username:
        return False
    return verify_password(password, expected_password_hash)


def get_basic_auth_credentials(authorization: Optional[str]) -> Optional[tuple[str, str]]:
    """Extract username and password from HTTP Basic Auth header."""
    if not authorization:
        return None
    
    try:
        scheme, credentials = authorization.split(' ', 1)
        if scheme.lower() != 'basic':
            return None
        
        decoded = base64.b64decode(credentials).decode('utf-8')
        username, password = decoded.split(':', 1)
        return username, password
    except Exception:
        return None
