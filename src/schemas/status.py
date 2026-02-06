"""Status and health check schemas."""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel
from enum import Enum


class JobStatus(str, Enum):
    """Job execution status."""
    IDLE = "idle"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobStatusResponse(BaseModel):
    """Single job status response."""
    job_id: str
    status: JobStatus
    message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration: Optional[float] = None
    result: Optional[Dict[str, Any]] = None


class ComponentStatus(BaseModel):
    """Status of a system component."""
    status: JobStatus
    message: str = "Ready"
    last_run: Optional[datetime] = None
    running: bool = False
    success: Optional[bool] = None
    duration: float = 0


class DatabaseStats(BaseModel):
    """Database statistics."""
    total_jobs: int
    total_companies: int
    last_updated: Optional[datetime] = None


class SyncStatus(BaseModel):
    """Sync status between local files and database."""
    checked: bool = False
    total_local: int = 0
    new_to_insert: int = 0
    already_in_db: int = 0
    sample_new: Optional[list] = None
    last_check: Optional[datetime] = None


class StatusResponse(BaseModel):
    """Complete system status."""
    scraper: ComponentStatus
    loader: ComponentStatus
    validator: ComponentStatus
    pipeline: ComponentStatus
    database: DatabaseStats
    sync: Optional[SyncStatus] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str
    timestamp: datetime
    database: bool
    redis: Optional[bool] = None


class PipelineResponse(BaseModel):
    """Response for pipeline execution."""
    job_ids: list[str]
    message: str
    steps: list[str]


class QueueStatusResponse(BaseModel):
    """Queue status response."""
    queued: int
    started: int
    finished: int
    failed: int
    queued_jobs: list[str] = []
    started_jobs: list[str]
    finished_jobs: list[str]
    failed_jobs: list[str]
