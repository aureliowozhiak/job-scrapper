"""Admin-only routes for scraping and job management."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from src.core.permissions import require_admin
import sqlite3

router = APIRouter(prefix="/api/admin", tags=["admin"])


class ScrapeRequest(BaseModel):
    """Request to start a scraping job."""
    query: str
    source: Optional[str] = None


class LoadRequest(BaseModel):
    """Request to load data into database."""
    file_path: str


class ValidateRequest(BaseModel):
    """Request to validate data."""
    date: Optional[str] = None


class SyncCheckRequest(BaseModel):
    """Request to check data synchronization."""
    pass


class PipelineRequest(BaseModel):
    """Request to run the full pipeline."""
    queries: List[str]


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    status: str


class SourcesResponse(BaseModel):
    """Response with available sources."""
    sources: List[str]


@router.post("/scrape", response_model=MessageResponse, dependencies=[Depends(require_admin)])
async def start_scrape(request: ScrapeRequest):
    """
    Start a web scraping job.
    
    Protected endpoint - requires admin authentication.
    """
    # TODO: Implement actual scraping logic
    return MessageResponse(
        message=f"Scraping started for query: {request.query}",
        status="success"
    )


@router.post("/load", response_model=MessageResponse, dependencies=[Depends(require_admin)])
async def load_data(request: LoadRequest):
    """
    Load scraped data into the database.
    
    Protected endpoint - requires admin authentication.
    """
    # TODO: Implement actual data loading logic
    return MessageResponse(
        message=f"Data loading started from: {request.file_path}",
        status="success"
    )


@router.post("/validate", response_model=MessageResponse, dependencies=[Depends(require_admin)])
async def validate_data(request: ValidateRequest):
    """
    Validate scraped data.
    
    Protected endpoint - requires admin authentication.
    """
    # TODO: Implement actual validation logic
    return MessageResponse(
        message="Data validation started",
        status="success"
    )


@router.post("/sync-check", response_model=MessageResponse, dependencies=[Depends(require_admin)])
async def sync_check(request: SyncCheckRequest):
    """
    Check data synchronization status.
    
    Protected endpoint - requires admin authentication.
    """
    # TODO: Implement actual sync check logic
    return MessageResponse(
        message="Sync check completed",
        status="success"
    )


@router.post("/pipeline", response_model=MessageResponse, dependencies=[Depends(require_admin)])
async def run_pipeline(request: PipelineRequest):
    """
    Run the complete data pipeline (scrape, transform, load).
    
    Protected endpoint - requires admin authentication.
    """
    # TODO: Implement actual pipeline logic
    return MessageResponse(
        message=f"Pipeline started for {len(request.queries)} queries",
        status="success"
    )


@router.delete("/job/{job_id}", response_model=MessageResponse, dependencies=[Depends(require_admin)])
async def delete_job(job_id: int):
    """
    Delete a specific job by ID.
    
    Protected endpoint - requires admin authentication.
    """
    try:
        with sqlite3.connect("jobs.db") as connection:
            cursor = connection.cursor()
            
            cursor.execute("DELETE FROM positions WHERE id = ?", (job_id,))
            connection.commit()
            
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        return MessageResponse(
            message=f"Job {job_id} deleted successfully",
            status="success"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.delete("/queue/failed", response_model=MessageResponse, dependencies=[Depends(require_admin)])
async def clear_failed_queue():
    """
    Clear the failed jobs queue.
    
    Protected endpoint - requires admin authentication.
    """
    # TODO: Implement actual queue clearing logic
    return MessageResponse(
        message="Failed queue cleared",
        status="success"
    )


@router.get("/sources", response_model=SourcesResponse)
async def get_sources():
    """
    Get list of available scraping sources.
    
    This endpoint is left public as per requirements (optional admin protection).
    """
    # TODO: Load from actual configuration
    return SourcesResponse(
        sources=["weworkremotely", "skipthedrive"]
    )
