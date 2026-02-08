"""RQ Job Manager for background task orchestration."""
from typing import Optional, Dict, Any, List
from redis import Redis
from rq import Queue
from rq.job import Job
from rq.registry import StartedJobRegistry, FinishedJobRegistry, FailedJobRegistry
from src.core.config import settings


class JobManager:
    """Manager for RQ background jobs."""
    
    def __init__(self):
        """Initialize job manager with Redis connection."""
        self.redis = Redis.from_url(settings.redis_url)
        self.queue = Queue('default', connection=self.redis)
    
    def enqueue_scraper(self, query: Optional[str] = None, region: Optional[str] = None, config: Optional[Dict] = None) -> str:
        """Enqueue scraping task."""
        from src.jobs.task_scraper import task_scraper
        
        job = self.queue.enqueue(
            task_scraper,
            query=query,
            region=region,
            config=config,
            job_timeout=settings.job_timeout,
            result_ttl=settings.job_result_ttl,
            job_id=f"scraper-{self._get_timestamp()}"
        )
        return job.id
    
    def enqueue_loader(self) -> str:
        """Enqueue loading task."""
        from src.jobs.task_loader import task_loader
        
        job = self.queue.enqueue(
            task_loader,
            job_timeout=settings.job_timeout,
            result_ttl=settings.job_result_ttl,
            job_id=f"loader-{self._get_timestamp()}"
        )
        return job.id
    
    def enqueue_validator(self) -> str:
        """Enqueue validation task."""
        from src.jobs.task_validator import task_validator
        
        job = self.queue.enqueue(
            task_validator,
            job_timeout=settings.job_timeout,
            result_ttl=settings.job_result_ttl,
            job_id=f"validator-{self._get_timestamp()}"
        )
        return job.id
    
    def enqueue_sync_check(self) -> str:
        """Enqueue sync check task."""
        from src.jobs.task_sync import task_sync_check
        
        job = self.queue.enqueue(
            task_sync_check,
            job_timeout=settings.job_timeout,
            result_ttl=settings.job_result_ttl,
            job_id=f"sync-{self._get_timestamp()}"
        )
        return job.id
    
    def enqueue_pipeline(self, query: Optional[str] = None, region: Optional[str] = None, config: Optional[Dict] = None) -> List[str]:
        """Enqueue full pipeline (scraper -> loader -> validator)."""
        from src.jobs.task_scraper import task_scraper
        from src.jobs.task_loader import task_loader
        from src.jobs.task_validator import task_validator
        
        job_ids = []
        
        # Enqueue scraper
        scraper_job = self.queue.enqueue(
            task_scraper,
            query=query,
            region=region,
            config=config,
            job_timeout=settings.job_timeout,
            result_ttl=settings.job_result_ttl,
            job_id=f"pipeline-scraper-{self._get_timestamp()}"
        )
        job_ids.append(scraper_job.id)
        
        # Enqueue loader (depends on scraper)
        loader_job = self.queue.enqueue(
            task_loader,
            depends_on=scraper_job,
            job_timeout=settings.job_timeout,
            result_ttl=settings.job_result_ttl,
            job_id=f"pipeline-loader-{self._get_timestamp()}"
        )
        job_ids.append(loader_job.id)
        
        # Enqueue validator (depends on loader)
        validator_job = self.queue.enqueue(
            task_validator,
            depends_on=loader_job,
            job_timeout=settings.job_timeout,
            result_ttl=settings.job_result_ttl,
            job_id=f"pipeline-validator-{self._get_timestamp()}"
        )
        job_ids.append(validator_job.id)
        
        return job_ids
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of a job."""
        try:
            job = Job.fetch(job_id, connection=self.redis)
            
            # Calculate duration
            duration = None
            if job.started_at:
                end_time = job.ended_at or datetime.now(timezone.utc)
                duration = round((end_time - job.started_at).total_seconds(), 2)
            
            return {
                "id": job.id,
                "status": job.get_status(),
                "result": job.result,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "ended_at": job.ended_at.isoformat() if job.ended_at else None,
                "duration": duration,
                "exc_info": job.exc_info if job.is_failed else None
            }
        except Exception as e:
            return {
                "id": job_id,
                "status": "not_found",
                "error": str(e)
            }
    
    def get_all_job_statuses(self) -> Dict[str, Any]:
        """Get status of all recent jobs."""
        started_registry = StartedJobRegistry(queue=self.queue)
        finished_registry = FinishedJobRegistry(queue=self.queue)
        failed_registry = FailedJobRegistry(queue=self.queue)
        
        return {
            "queued": len(self.queue),
            "started": len(started_registry),
            "finished": len(finished_registry),
            "failed": len(failed_registry),
            "queued_jobs": list(self.queue.get_job_ids()),
            "started_jobs": list(started_registry.get_job_ids()),
            "finished_jobs": list(finished_registry.get_job_ids())[-50:],  # Last 50
            "failed_jobs": list(failed_registry.get_job_ids())[-50:]  # Last 50
        }
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job."""
        try:
            job = Job.fetch(job_id, connection=self.redis)
            job.cancel()
            return True
        except Exception:
            return False
    
    def clear_failed_jobs(self):
        """Clear all failed jobs."""
        failed_registry = FailedJobRegistry(queue=self.queue)
        for job_id in failed_registry.get_job_ids():
            failed_registry.remove(job_id, delete_job=True)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for job IDs."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


# Global job manager instance
job_manager = JobManager()
