"""Admin and control routes for managing scraping jobs."""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from src.jobs.manager import job_manager
from src.schemas.status import JobStatusResponse, PipelineResponse, QueueStatusResponse
from src.core.permissions import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])


@router.post("/scrape", response_model=JobStatusResponse)
async def trigger_scrape(params: Optional[Dict[str, Any]] = None):
    """Trigger scraping job with optional filters."""
    try:
        query = params.get("query") if params else None
        region = params.get("region") if params else None
        config = params.get("config") if params else None
        
        job_id = job_manager.enqueue_scraper(query=query, region=region, config=config)
        return JobStatusResponse(
            job_id=job_id,
            message=f"Scraping job enqueued (query: {query or 'default'})",
            status="queued"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enqueue job: {str(e)}")


@router.post("/load", response_model=JobStatusResponse)
async def trigger_load():
    """Trigger loading job."""
    try:
        job_id = job_manager.enqueue_loader()
        return JobStatusResponse(
            job_id=job_id,
            message="Loading job enqueued",
            status="queued"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enqueue job: {str(e)}")


@router.post("/validate", response_model=JobStatusResponse)
async def trigger_validate():
    """Trigger validation job."""
    try:
        job_id = job_manager.enqueue_validator()
        return JobStatusResponse(
            job_id=job_id,
            message="Validation job enqueued",
            status="queued"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enqueue job: {str(e)}")


@router.post("/sync-check", response_model=JobStatusResponse)
async def trigger_sync_check():
    """Trigger sync check job."""
    try:
        job_id = job_manager.enqueue_sync_check()
        return JobStatusResponse(
            job_id=job_id,
            message="Sync check job enqueued",
            status="queued"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enqueue job: {str(e)}")


@router.post("/pipeline", response_model=PipelineResponse)
async def trigger_pipeline(params: Optional[Dict[str, Any]] = None):
    """Trigger full pipeline (scrape -> validate) with optional filters.
    
    Note: Scraper now loads data directly to database, so loader step is integrated.
    """
    try:
        query = params.get("query") if params else None
        region = params.get("region") if params else None
        config = params.get("config") if params else None
        
        job_ids = job_manager.enqueue_pipeline(query=query, region=region, config=config)
        return PipelineResponse(
            job_ids=job_ids,
            message=f"Pipeline enqueued (query: {query or 'default'})",
            steps=["scraper", "validator"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enqueue pipeline: {str(e)}")


@router.get("/job/{job_id}", response_model=dict)
async def get_job_status(job_id: str):
    """Get status of a specific job."""
    status = job_manager.get_job_status(job_id)
    return status


@router.get("/queue/status", response_model=QueueStatusResponse)
async def get_queue_status():
    """Get overall queue status."""
    status = job_manager.get_all_job_statuses()
    return QueueStatusResponse(**status)


@router.get("/pipelines")
async def get_pipeline_groups():
    """Get task groups (pipelines) for Task Manager dashboard.
    
    Returns only pipeline groups, not individual standalone tasks.
    Each pipeline contains scrape, validate, load, and cleanup tasks with aggregated stats.
    """
    try:
        pipelines = job_manager.get_pipeline_groups()
        return {"pipelines": pipelines, "total": len(pipelines)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get pipelines: {str(e)}")


@router.delete("/job/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a running job."""
    success = job_manager.cancel_job(job_id)
    if success:
        return {"message": f"Job {job_id} cancelled"}
    raise HTTPException(status_code=404, detail="Job not found or cannot be cancelled")


@router.delete("/queue/failed")
async def clear_failed_jobs():
    """Clear all failed jobs from the queue."""
    job_manager.clear_failed_jobs()
    return {"message": "Failed jobs cleared"}


@router.get("/sources")
async def get_sources():
    """Get all available scraping sources/spiders."""
    try:
        from src.etl.scrapy_runner import SPIDER_CONFIG
        return SPIDER_CONFIG
    except ImportError:
        return {}
