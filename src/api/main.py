"""Main FastAPI application with authentication and routing."""
from fastapi import FastAPI, Request, Form, HTTPException, status, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from src.core.config import settings
from src.core.auth import verify_credentials
from src.core.permissions import get_optional_admin
from src.api.routes import admin, health, jobs
import os

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Job Scrapper API with Role-Based Access Control",
    version="1.0.0"
)

# Add session middleware for authentication
if not settings.session_secret_key:
    raise ValueError(
        "SESSION_SECRET_KEY must be set. "
        "Generate one using: python -c \"import secrets; print(secrets.token_hex(32))\""
    )

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret_key
)

# Setup templates
templates = Jinja2Templates(directory="templates")

# Include routers
app.include_router(jobs.router)
app.include_router(admin.router)
app.include_router(health.router)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request, is_admin: bool = Depends(get_optional_admin)):
    """
    Render the main application page.
    
    Shows Job Feed to all users.
    Shows Task Manager and Health Monitor only to admin users.
    """
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "is_admin": is_admin,
            "app_name": settings.app_name
        }
    )


@app.post("/api/auth/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    """
    Authenticate user and create admin session.
    
    Args:
        username: The username
        password: The password
    
    Returns:
        Success message and redirect URL
    
    Raises:
        HTTPException: 401 if credentials are invalid
    """
    # Verify credentials
    if not verify_credentials(
        username,
        password,
        settings.admin_username,
        settings.admin_password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Set admin session
    request.session["is_admin"] = True
    
    return JSONResponse(
        content={
            "message": "Login successful",
            "redirect": "/"
        },
        status_code=200
    )


@app.post("/api/auth/logout")
async def logout(request: Request):
    """
    Clear admin session.
    
    Returns:
        Success message
    """
    # Clear session
    request.session.clear()
    
    return JSONResponse(
        content={
            "message": "Logout successful",
            "redirect": "/"
        },
        status_code=200
    )


@app.get("/api/auth/status")
async def auth_status(request: Request, is_admin: bool = Depends(get_optional_admin)):
    """
    Get current authentication status.
    
    Returns:
        Authentication status information
    """
    return {
        "is_admin": is_admin,
        "admin_enabled": settings.admin_enabled
    }


# Health check at root API
@app.get("/api")
async def api_root():
    """API root endpoint."""
    return {
        "message": "Job Scrapper API",
        "version": "1.0.0",
        "endpoints": {
            "jobs": "/api/jobs",
            "admin": "/api/admin",
            "health": "/api/health",
            "auth": "/api/auth"
        }
    }
