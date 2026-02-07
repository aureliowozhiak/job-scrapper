"""Permission decorators and dependencies for FastAPI endpoints."""
from fastapi import Request, HTTPException, status
from src.core.config import settings


def require_admin(request: Request) -> bool:
    """
    FastAPI dependency that requires admin authentication.
    
    This dependency checks if the user is authenticated as an admin via session.
    Raises 403 Forbidden if not authenticated or admin is disabled.
    
    Args:
        request: The FastAPI request object
    
    Returns:
        True if the user is an admin
    
    Raises:
        HTTPException: 403 if not authenticated as admin or admin is disabled
    """
    # Check if admin is enabled
    if not settings.admin_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is disabled"
        )
    
    # Check if user has admin session
    is_admin = request.session.get("is_admin", False)
    
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required. Please login."
        )
    
    return True


def get_optional_admin(request: Request) -> bool:
    """
    FastAPI dependency that returns admin status without requiring it.
    
    This is useful for templates and endpoints that need to know if the user
    is an admin but don't require admin access.
    
    Args:
        request: The FastAPI request object
    
    Returns:
        True if the user is an admin, False otherwise
    """
    if not settings.admin_enabled:
        return False
    
    return request.session.get("is_admin", False)
