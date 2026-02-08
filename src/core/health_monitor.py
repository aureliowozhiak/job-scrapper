"""Health monitoring service for scrapers and system components."""
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from sqlalchemy import func, text
from sqlalchemy.orm import Session
from src.database.models import Position
from src.database.connection import SessionLocal
from src.etl.scrapy_runner import SPIDER_CONFIG
from src.schemas.health import ScraperMetrics, SystemHealth, HealthDashboardResponse
from src.jobs.manager import job_manager
from src.core.logging import get_logger
from redis import Redis
from src.core.config import settings

logger = get_logger(__name__)


class HealthMonitor:
    """Monitor health of scrapers and system components."""
    
    def __init__(self):
        self.spider_config = SPIDER_CONFIG
    
    def get_scraper_metrics(self, db: Session) -> List[ScraperMetrics]:
        """Get health metrics for all scrapers."""
        metrics = []
        
        for scraper_id, config in self.spider_config.items():
            # Get total jobs from this scraper
            source_name = config["nice_name"]
            total_jobs = db.query(func.count(Position.id))\
                .filter(Position.source == source_name)\
                .scalar() or 0
            
            # Get last 24h stats
            yesterday = datetime.now(timezone.utc) - timedelta(hours=24)
            
            jobs_24h = db.query(func.count(Position.id))\
                .filter(Position.source == source_name)\
                .filter(Position.created_at >= yesterday)\
                .scalar() or 0
            
            # Get last run info from Redis/RQ (would need job history tracking)
            # For now, we'll use basic metrics
            last_run_time = None
            last_run_status = None
            last_run_duration = None
            last_run_jobs_count = jobs_24h  # Approximate
            
            # Calculate success rate (simplified - would need job tracking)
            success_rate_24h = 100.0 if total_jobs > 0 else 0.0
            
            metrics.append(ScraperMetrics(
                scraper_id=scraper_id,
                scraper_name=config["nice_name"],
                domain=config["domain"],
                is_active=config.get("active", True),
                total_jobs_scraped=total_jobs,
                last_run_time=last_run_time,
                last_run_status=last_run_status,
                last_run_duration=last_run_duration,
                last_run_jobs_count=last_run_jobs_count,
                success_rate_24h=success_rate_24h,
                avg_response_time=None,
                error_count_24h=0,
                last_error=None,
                note=config.get("note")
            ))
        
        return metrics
    
    def get_system_health(self, db: Session) -> SystemHealth:
        """Get overall system health status."""
        # Check database
        db_status = "connected"
        try:
            db.execute(text("SELECT 1"))
        except Exception as e:
            db_status = f"error: {str(e)}"
            logger.error(f"Database health check failed: {e}")
        
        # Check Redis
        redis_status = "connected"
        try:
            redis = Redis.from_url(settings.redis_url)
            redis.ping()
        except Exception as e:
            redis_status = f"error: {str(e)}"
            logger.error(f"Redis health check failed: {e}")
        
        # Get queue status
        queue_status = job_manager.get_all_job_statuses()
        
        # Get total jobs
        total_jobs = db.query(func.count(Position.id)).scalar() or 0
        
        # Count active scrapers
        total_scrapers = len(self.spider_config)
        active_scrapers = sum(1 for cfg in self.spider_config.values() if cfg.get("active", True))
        
        # Determine overall status
        status = "healthy"
        if db_status != "connected" or redis_status != "connected":
            status = "unhealthy"
        elif queue_status.get("failed", 0) > 5:
            status = "degraded"
        
        return SystemHealth(
            status=status,
            timestamp=datetime.now(timezone.utc),
            database_status=db_status,
            redis_status=redis_status,
            queue_status={
                "queued": queue_status.get("queued", 0),
                "running": queue_status.get("started", 0),
                "finished": queue_status.get("finished", 0),
                "failed": queue_status.get("failed", 0)
            },
            total_jobs=total_jobs,
            total_scrapers=total_scrapers,
            active_scrapers=active_scrapers
        )
    
    def get_dashboard_data(self) -> HealthDashboardResponse:
        """Get complete health dashboard data."""
        with SessionLocal() as db:
            system = self.get_system_health(db)
            scrapers = self.get_scraper_metrics(db)
            
            return HealthDashboardResponse(
                system=system,
                scrapers=scrapers
            )


# Global instance
health_monitor = HealthMonitor()
