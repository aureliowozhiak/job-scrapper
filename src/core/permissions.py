"""Permission decorators and dependencies for FastAPI endpoints."""
from fastapi import Request, HTTPException, status, Depends
from src.core.config import settings


async def require_admin(request: Request) -> bool:
    """FastAPI dependency that requires admin authentication."""
    if not settings.admin_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is disabled"
        )
    
    is_admin = request.session.get("is_admin", False)
    
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required. Please login."
        )
    
    return True


async def get_optional_admin(request: Request) -> bool:
    """FastAPI dependency that returns admin status without requiring it."""
    if not settings.admin_enabled:
        return False
    
    return request.session.get("is_admin", False)
