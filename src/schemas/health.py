"""Health monitoring schemas."""
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime


class ScraperMetrics(BaseModel):
    """Metrics for a single scraper."""
    scraper_id: str
    scraper_name: str
    domain: str
    is_active: bool
    total_jobs_scraped: int
    last_run_time: Optional[datetime] = None
    last_run_status: Optional[str] = None
    last_run_duration: Optional[float] = None
    last_run_jobs_count: Optional[int] = None
    success_rate_24h: Optional[float] = None
    avg_response_time: Optional[float] = None
    error_count_24h: int = 0
    last_error: Optional[str] = None
    note: Optional[str] = None


class SystemHealth(BaseModel):
    """Overall system health status."""
    status: str  # 'healthy', 'degraded', 'unhealthy'
    timestamp: datetime
    database_status: str
    redis_status: str
    queue_status: Dict[str, int]
    total_jobs: int
    total_scrapers: int
    active_scrapers: int


class HealthDashboardResponse(BaseModel):
    """Complete health monitoring dashboard data."""
    system: SystemHealth
    scrapers: List[ScraperMetrics]
