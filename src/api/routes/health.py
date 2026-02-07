"""Health check and monitoring routes."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from src.core.permissions import require_admin
import sqlite3
import os

router = APIRouter(prefix="/api/health", tags=["health"])


class HealthStatus(BaseModel):
    """Health status response."""
    status: str
    message: Optional[str] = None


class DatabaseHealth(BaseModel):
    """Database health information."""
    status: str
    connected: bool
    tables: int
    message: Optional[str] = None


class RedisHealth(BaseModel):
    """Redis health information."""
    status: str
    connected: bool
    message: Optional[str] = None


class DashboardStats(BaseModel):
    """Dashboard statistics."""
    total_jobs: int
    db_status: str
    redis_status: str


@router.get("/", response_model=HealthStatus)
async def health_check():
    """
    Basic health check endpoint.
    
    Public endpoint - no authentication required.
    """
    return HealthStatus(
        status="healthy",
        message="Application is running"
    )


@router.get("/db", response_model=DatabaseHealth)
async def database_health():
    """
    Check database health.
    
    Public endpoint - no authentication required.
    """
    try:
        connection = sqlite3.connect("jobs.db")
        cursor = connection.cursor()
        
        # Check if we can query the database
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        connection.close()
        
        return DatabaseHealth(
            status="healthy",
            connected=True,
            tables=len(tables),
            message=f"Database connected with {len(tables)} tables"
        )
    except Exception as e:
        return DatabaseHealth(
            status="unhealthy",
            connected=False,
            tables=0,
            message=f"Database error: {str(e)}"
        )


@router.get("/redis", response_model=RedisHealth)
async def redis_health():
    """
    Check Redis health.
    
    Public endpoint - no authentication required.
    Note: This is a placeholder as Redis is not currently configured.
    """
    return RedisHealth(
        status="not_configured",
        connected=False,
        message="Redis is not configured"
    )


@router.get("/dashboard", response_model=DashboardStats, dependencies=[Depends(require_admin)])
async def health_dashboard():
    """
    Get comprehensive health dashboard statistics.
    
    Protected endpoint - requires admin authentication.
    """
    total_jobs = 0
    db_status = "unknown"
    
    try:
        connection = sqlite3.connect("jobs.db")
        cursor = connection.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM positions")
        total_jobs = cursor.fetchone()[0]
        
        connection.close()
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"
    
    return DashboardStats(
        total_jobs=total_jobs,
        db_status=db_status,
        redis_status="not_configured"
    )
