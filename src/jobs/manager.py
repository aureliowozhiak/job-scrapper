"""RQ Job Manager for background task orchestration."""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
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
        # Dedicated pipeline queue for sequential execution within pipeline groups
        self.pipeline_queue = Queue('pipeline', connection=self.redis)
    
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
        """Enqueue full pipeline (scraper -> validator -> loader).
        
        Pipeline flow:
        1. Scraper: Scrapes jobs and saves to JSON files (data/output/<timestamp>)
        2. Validator: Validates scraped JSON files (optional link validation)
        3. Loader: Loads validated data from JSON files to database
        4. Cleanup: Removes JSON files after successful load
        
        Each pipeline run gets its own unique output directory to avoid interference.
        """
        from src.jobs.task_scraper import task_scraper
        from src.jobs.task_validator import task_validator
        from src.jobs.task_loader import task_loader
        from src.jobs.task_cleanup import task_cleanup
        
        job_ids = []
        timestamp = self._get_timestamp()
        pipeline_id = f"pipeline-{timestamp}"
        
        # Create unique output directory for this pipeline run
        from src.core.config import settings
        from pathlib import Path
        from datetime import datetime, timezone
        
        now = datetime.now(timezone.utc)
        # Use pipeline_id as unique subdirectory: data/output/2026/2/9/pipeline-20260209123456
        output_dir = Path(settings.output_path) / str(now.year) / str(now.month) / str(now.day) / pipeline_id
        
        # Use dedicated pipeline queue for sequential execution
        # Step 1: Enqueue scraper (scrapes to JSON files in unique directory)
        scraper_job = self.pipeline_queue.enqueue(
            task_scraper,
            query=query,
            region=region,
            config=config,
            output_dir=str(output_dir),  # Pass unique directory
            job_timeout=settings.job_timeout,
            result_ttl=settings.job_result_ttl,
            job_id=f"{pipeline_id}-scrape",
            meta={"pipeline_id": pipeline_id, "step": "scrape", "output_dir": str(output_dir)},
            at_front=False  # FIFO ordering
        )
        job_ids.append(scraper_job.id)
        
        # Step 2: Enqueue validator (validates scraped JSON files, depends on scraper)
        validator_job = self.pipeline_queue.enqueue(
            task_validator,
            output_dir=str(output_dir),  # Use same directory
            depends_on=scraper_job,
            job_timeout=settings.job_timeout,
            result_ttl=settings.job_result_ttl,
            job_id=f"{pipeline_id}-validate",
            meta={"pipeline_id": pipeline_id, "step": "validate", "output_dir": str(output_dir)},
            at_front=False  # FIFO ordering
        )
        job_ids.append(validator_job.id)
        
        # Step 3: Enqueue loader (loads validated data to DB, depends on validator)
        loader_job = self.pipeline_queue.enqueue(
            task_loader,
            output_dir=str(output_dir),  # Use same directory
            depends_on=validator_job,
            job_timeout=settings.job_timeout,
            result_ttl=settings.job_result_ttl,
            job_id=f"{pipeline_id}-load",
            meta={"pipeline_id": pipeline_id, "step": "load", "output_dir": str(output_dir)},
            at_front=False  # FIFO ordering
        )
        job_ids.append(loader_job.id)
        
        # Step 4: Enqueue cleanup (removes JSON files after successful load)
        cleanup_job = self.pipeline_queue.enqueue(
            task_cleanup,
            output_dir=str(output_dir),
            depends_on=loader_job,
            job_timeout=300,  # 5 minutes should be plenty
            result_ttl=settings.job_result_ttl,
            job_id=f"{pipeline_id}-cleanup",
            meta={"pipeline_id": pipeline_id, "step": "cleanup", "output_dir": str(output_dir)},
            at_front=False  # FIFO ordering
        )
        job_ids.append(cleanup_job.id)
        
        return job_ids
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of a job with enriched metrics."""
        try:
            job = Job.fetch(job_id, connection=self.redis)
            
            # Helper to ensure datetime is timezone-aware in UTC
            def make_aware(dt):
                if dt is None:
                    return None
                if dt.tzinfo is None:
                    # Naive datetime - assume UTC
                    return dt.replace(tzinfo=timezone.utc)
                # Already aware - convert to UTC
                return dt.astimezone(timezone.utc)
            
            # Make all datetimes timezone-aware and in UTC
            created_at = make_aware(job.created_at)
            enqueued_at = make_aware(job.enqueued_at)
            started_at = make_aware(job.started_at)
            ended_at = make_aware(job.ended_at)
            
            # Calculate duration
            duration = None
            if started_at:
                try:
                    end_time = ended_at if ended_at else datetime.now(timezone.utc)
                    duration = round((end_time - started_at).total_seconds(), 2)
                except Exception as e:
                    # Fallback if datetime arithmetic fails
                    duration = None
            
            # Detect job type from job_id
            job_type = self._detect_job_type(job.id)
            
            # Extract enriched metrics from result
            enriched = self._extract_metrics(job.result, job_type) if job.result else {}
            
            return {
                "id": job.id,
                "status": job.get_status(),
                "result": job.result,
                "created_at": created_at.isoformat() if created_at else None,
                "enqueued_at": enqueued_at.isoformat() if enqueued_at else None,
                "started_at": started_at.isoformat() if started_at else None,
                "ended_at": ended_at.isoformat() if ended_at else None,
                "duration": duration,
                "exc_info": job.exc_info if job.is_failed else None,
                **enriched  # Add enriched metrics
            }
        except Exception as e:
            return {
                "id": job_id,
                "status": "not_found",
                "error": str(e)
            }
    
    def _detect_job_type(self, job_id: str) -> str:
        """Detect job type from job ID."""
        job_id_lower = job_id.lower()
        if "scraper" in job_id_lower or "scrape" in job_id_lower:
            return "scraper"
        elif "loader" in job_id_lower or "load" in job_id_lower:
            return "loader"
        elif "validator" in job_id_lower or "validate" in job_id_lower:
            return "validator"
        elif "sync" in job_id_lower:
            return "sync"
        elif "pipeline" in job_id_lower:
            return "pipeline"
        return "unknown"
    
    def _extract_metrics(self, result: Dict[str, Any], job_type: str) -> Dict[str, Any]:
        """Extract enriched metrics from job result based on job type."""
        if not isinstance(result, dict):
            return {}
        
        # Extract stats from nested structure if present
        stats = result.get("stats", result)
        
        enriched = {"job_type": job_type}
        
        if job_type == "scraper":
            jobs_scraped = stats.get("jobs_scraped", 0)
            
            enriched["jobs_processed"] = jobs_scraped
            enriched["success_rate"] = 100.0 if jobs_scraped > 0 else 0.0
            enriched["detailed_stats"] = {
                "queries_processed": stats.get("queries_processed", 0),
                "jobs_scraped": jobs_scraped,
                "spiders": stats.get("spiders", {}),
                "output_directory": stats.get("output_directory", "")
            }
            
        elif job_type == "loader":
            processed = stats.get("processed", 0)
            inserted = stats.get("inserted", 0)
            
            enriched["jobs_processed"] = processed
            enriched["success_rate"] = round((inserted / processed * 100), 2) if processed > 0 else 0
            enriched["detailed_stats"] = {
                "processed": processed,
                "inserted": inserted,
                "duplicates": stats.get("duplicates", 0),
                "errors": stats.get("errors", 0),
                "pre_rejected": stats.get("pre_rejected", 0),
                "db_before": stats.get("db_before", 0),
                "db_after": stats.get("db_after", 0),
                "db_new_jobs": stats.get("db_new_jobs", 0)
            }
            
        elif job_type == "validator":
            total_jobs = stats.get("total_jobs", 0)
            valid_jobs = stats.get("valid_jobs", 0)
            duplicates_removed = stats.get("duplicates_removed", 0)
            
            enriched["jobs_processed"] = total_jobs
            enriched["success_rate"] = round((valid_jobs / total_jobs * 100), 2) if total_jobs > 0 else 0
            enriched["detailed_stats"] = {
                "files_found": stats.get("files_found", 0),
                "files_validated": stats.get("files_validated", 0),
                "total_jobs": total_jobs,
                "valid_jobs": valid_jobs,
                "invalid_jobs": stats.get("invalid_jobs", 0),
                "duplicates_removed": duplicates_removed,
                "errors": stats.get("errors", [])
            }
        
        elif job_type == "cleanup":
            files_removed = stats.get("files_removed", 0)
            
            enriched["jobs_processed"] = files_removed
            enriched["success_rate"] = 100.0 if files_removed > 0 else 0.0
            enriched["detailed_stats"] = {
                "files_removed": files_removed,
                "status": stats.get("status", "unknown"),
                "message": stats.get("message", "")
            }
        
        return enriched
    
    def get_all_job_statuses(self) -> Dict[str, Any]:
        """Get status summary - counts unique pipeline groups, not individual tasks.
        
        This method is used for dashboard statistics display.
        Returns counts by grouping pipeline tasks together.
        """
        started_registry = StartedJobRegistry(queue=self.queue)
        finished_registry = FinishedJobRegistry(queue=self.queue)
        failed_registry = FailedJobRegistry(queue=self.queue)
        
        # Also check pipeline queue
        pipeline_started_registry = StartedJobRegistry(queue=self.pipeline_queue)
        pipeline_finished_registry = FinishedJobRegistry(queue=self.pipeline_queue)
        pipeline_failed_registry = FailedJobRegistry(queue=self.pipeline_queue)
        
        # Get all job IDs from both queues
        all_job_ids = (
            list(self.queue.get_job_ids()) + 
            list(self.pipeline_queue.get_job_ids()) +
            list(started_registry.get_job_ids()) + 
            list(pipeline_started_registry.get_job_ids()) +
            list(finished_registry.get_job_ids()) + 
            list(pipeline_finished_registry.get_job_ids()) +
            list(failed_registry.get_job_ids()) + 
            list(pipeline_failed_registry.get_job_ids())
        )
        
        # Group by pipeline ID to avoid counting individual tasks
        pipeline_ids = set()
        queued_pipelines = set()
        started_pipelines = set()
        finished_pipelines = set()
        failed_pipelines = set()
        
        for job_id in all_job_ids:
            # Extract pipeline ID (format: pipeline-YYYYMMDDHHMMSS-step)
            if job_id.startswith("pipeline-"):
                parts = job_id.split("-")
                if len(parts) >= 3 and parts[1].isdigit() and len(parts[1]) == 14:
                    pipeline_id = f"{parts[0]}-{parts[1]}"
                    pipeline_ids.add(pipeline_id)
                    
                    # Determine pipeline status by checking individual task
                    try:
                        job = Job.fetch(job_id, connection=self.redis)
                        status = job.get_status()
                        
                        if status in ["queued", "scheduled"]:
                            queued_pipelines.add(pipeline_id)
                        elif status == "started":
                            started_pipelines.add(pipeline_id)
                        elif status == "finished":
                            finished_pipelines.add(pipeline_id)
                        elif status == "failed":
                            failed_pipelines.add(pipeline_id)
                    except:
                        pass
        
        # A pipeline is:
        # - Queued if ANY task is queued (and none started/running)
        # - Running if ANY task is started/running
        # - Failed if ANY task failed
        # - Finished only if ALL tasks finished
        
        # Resolve overlapping statuses (priority: failed > running > queued > finished)
        running_final = started_pipelines - failed_pipelines
        queued_final = queued_pipelines - failed_pipelines - started_pipelines
        finished_final = finished_pipelines - failed_pipelines - started_pipelines - queued_pipelines
        
        return {
            "queued": len(queued_final),
            "started": len(running_final),
            "finished": len(finished_final),
            "failed": len(failed_pipelines),
            "queued_jobs": list(queued_final),
            "started_jobs": list(running_final),
            "finished_jobs": list(finished_final)[-50:],
            "failed_jobs": list(failed_pipelines)[-50:]
        }
    
    def get_pipeline_groups(self) -> List[Dict[str, Any]]:
        """Get task groups (pipelines) instead of individual tasks.
        
        Returns only pipeline groups, not standalone tasks.
        Each group aggregates stats from scrape, validate, load, and cleanup tasks.
        """
        from collections import defaultdict
        
        # Get all job IDs directly from registries (avoid circular dependency)
        started_registry = StartedJobRegistry(queue=self.queue)
        finished_registry = FinishedJobRegistry(queue=self.queue)
        failed_registry = FailedJobRegistry(queue=self.queue)
        
        pipeline_started_registry = StartedJobRegistry(queue=self.pipeline_queue)
        pipeline_finished_registry = FinishedJobRegistry(queue=self.pipeline_queue)
        pipeline_failed_registry = FailedJobRegistry(queue=self.pipeline_queue)
        
        all_job_ids = (
            list(self.queue.get_job_ids()) + 
            list(self.pipeline_queue.get_job_ids()) +
            list(started_registry.get_job_ids()) + 
            list(pipeline_started_registry.get_job_ids()) +
            list(finished_registry.get_job_ids()) + 
            list(pipeline_finished_registry.get_job_ids()) +
            list(failed_registry.get_job_ids()) + 
            list(pipeline_failed_registry.get_job_ids())
        )
        
        # Group by pipeline ID
        pipeline_groups = defaultdict(lambda: {
            "tasks": [],
            "pipeline_id": None,
            "started_at": None,
            "ended_at": None,
            "total_jobs_processed": 0,
            "total_inserted": 0,
            "total_duplicates": 0,
            "db_before": 0,
            "db_after": 0,
            # Validator stats
            "valid_jobs": 0,
            "invalid_jobs": 0,
            "duplicates_removed": 0,
            # Cleanup stats
            "files_removed": 0
        })
        
        for job_id in all_job_ids:
            # Only process pipeline tasks (format: pipeline-TIMESTAMP-STEP)
            if not job_id.startswith("pipeline-"):
                continue
                
            # Extract pipeline ID (e.g., "pipeline-20260209123456" from "pipeline-20260209123456-scrape")
            # NEW format: pipeline-YYYYMMDDHHMMSS-step (e.g., pipeline-20260209123456-scrape)
            # OLD format: pipeline-step-YYYYMMDDHHMMSS (e.g., pipeline-scraper-20260206012459) - SKIP THESE
            parts = job_id.split("-")
            if len(parts) < 3:
                continue  # Skip malformed IDs
            
            # Check if parts[1] is a 14-digit timestamp (new format) or a step name (old format)
            if not parts[1].isdigit() or len(parts[1]) != 14:
                # Old format with step name in parts[1] - skip these legacy tasks
                continue
                
            # Pipeline ID is first 2 parts: "pipeline-YYYYMMDDHHMMSS"
            pipeline_id = f"{parts[0]}-{parts[1]}"
            # Step is everything after the second dash (handles "scrape", "validate", "load", "cleanup")
            step = "-".join(parts[2:]) if len(parts) > 2 else "unknown"
            
            job_status = self.get_job_status(job_id)
            
            # Initialize pipeline group
            if pipeline_groups[pipeline_id]["pipeline_id"] is None:
                pipeline_groups[pipeline_id]["pipeline_id"] = pipeline_id
            
            # Add task to group
            pipeline_groups[pipeline_id]["tasks"].append({
                "step": step,
                "job_id": job_id,
                "status": job_status.get("status"),
                "started_at": job_status.get("started_at"),
                "ended_at": job_status.get("ended_at"),
                "duration": job_status.get("duration"),
                "detailed_stats": job_status.get("detailed_stats", {})
            })
            
            # Update pipeline-level timestamps
            if job_status.get("started_at"):
                if pipeline_groups[pipeline_id]["started_at"] is None:
                    pipeline_groups[pipeline_id]["started_at"] = job_status["started_at"]
                else:
                    pipeline_groups[pipeline_id]["started_at"] = min(
                        pipeline_groups[pipeline_id]["started_at"], 
                        job_status["started_at"]
                    )
            
            if job_status.get("ended_at"):
                if pipeline_groups[pipeline_id]["ended_at"] is None:
                    pipeline_groups[pipeline_id]["ended_at"] = job_status["ended_at"]
                else:
                    pipeline_groups[pipeline_id]["ended_at"] = max(
                        pipeline_groups[pipeline_id]["ended_at"],
                        job_status["ended_at"]
                    )
            
            # Aggregate stats from individual tasks
            detailed_stats = job_status.get("detailed_stats", {})
            if step == "scrape":
                # Only set (not add) the jobs_scraped count
                pipeline_groups[pipeline_id]["total_jobs_processed"] = detailed_stats.get("jobs_scraped", 0)
            elif step == "validate":
                # Set validator stats
                pipeline_groups[pipeline_id]["valid_jobs"] = detailed_stats.get("valid_jobs", 0)
                pipeline_groups[pipeline_id]["invalid_jobs"] = detailed_stats.get("invalid_jobs", 0)
                pipeline_groups[pipeline_id]["duplicates_removed"] = detailed_stats.get("duplicates_removed", 0)
            elif step == "load":
                # Only set (not add) the load stats - use correct keys from load task
                pipeline_groups[pipeline_id]["total_inserted"] = detailed_stats.get("inserted", 0)
                pipeline_groups[pipeline_id]["total_duplicates"] = detailed_stats.get("duplicates", 0)
                pipeline_groups[pipeline_id]["db_before"] = detailed_stats.get("db_before", 0)
                pipeline_groups[pipeline_id]["db_after"] = detailed_stats.get("db_after", 0)
            elif step == "cleanup":
                # Set cleanup stats
                pipeline_groups[pipeline_id]["files_removed"] = detailed_stats.get("files_removed", 0)
        
        # Convert to list and sort by pipeline_id (descending, most recent first)
        result = []
        for pipeline_id, group_data in sorted(pipeline_groups.items(), reverse=True):
            # Calculate overall pipeline status
            task_statuses = [t["status"] for t in group_data["tasks"]]
            if any(s == "failed" for s in task_statuses):
                overall_status = "failed"
            elif any(s in ["started", "queued"] for s in task_statuses):
                overall_status = "running"
            elif all(s == "finished" for s in task_statuses):
                overall_status = "finished"
            else:
                overall_status = "unknown"
            
            # Sort tasks by step order
            step_order = {"scrape": 0, "validate": 1, "load": 2, "cleanup": 3}
            group_data["tasks"].sort(key=lambda t: step_order.get(t["step"], 99))
            
            # Calculate progress based on completed steps (excluding cleanup for simplicity)
            main_tasks = [t for t in group_data["tasks"] if t["step"] != "cleanup"]
            completed_main_tasks = sum(1 for t in main_tasks if t["status"] == "finished")
            progress_percent = (completed_main_tasks / len(main_tasks) * 100) if main_tasks else 0
            
            result.append({
                "pipeline_id": pipeline_id,
                "status": overall_status,
                "started_at": group_data["started_at"],
                "ended_at": group_data["ended_at"],
                "tasks": group_data["tasks"],
                "total_jobs_processed": group_data["total_jobs_processed"],
                "total_inserted": group_data["total_inserted"],
                "total_duplicates": group_data["total_duplicates"],
                "db_before": group_data["db_before"],
                "db_after": group_data["db_after"],
                # Validator stats
                "valid_jobs": group_data["valid_jobs"],
                "invalid_jobs": group_data["invalid_jobs"],
                "duplicates_removed": group_data["duplicates_removed"],
                # Cleanup stats
                "files_removed": group_data["files_removed"],
                "progress_percent": round(progress_percent, 1),
                "completed_steps": f"{completed_main_tasks}/{len(main_tasks)}"
            })
        
        return result[:50]  # Return last 50 pipelines
    
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
