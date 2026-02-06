"""Job search and listing routes."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from src.database.connection import get_db
from src.database.repositories import PositionRepository
from src.schemas.job import Job, JobList, JobStats

router = APIRouter()


@router.get("/search", response_model=List[Job])
async def search_jobs(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Search jobs by title or company."""
    repo = PositionRepository(db)
    positions = repo.search(q, limit=limit, offset=offset)
    return [Job.model_validate(p) for p in positions]


@router.get("/", response_model=JobList)
async def list_jobs(
    search: Optional[str] = None,
    company: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List all jobs with optional filters."""
    repo = PositionRepository(db)
    positions = repo.get_all(limit=limit, offset=offset, search=search, company=company)
    total = repo.count(search=search, company=company)
    
    return JobList(
        jobs=[Job.model_validate(p) for p in positions],
        total=total,
        count=len(positions),
        limit=limit,
        offset=offset
    )


@router.get("/stats", response_model=JobStats)
async def get_stats(db: Session = Depends(get_db)):
    """Get database statistics."""
    repo = PositionRepository(db)
    stats = repo.get_stats()
    return JobStats(**stats)


@router.get("/{job_id}", response_model=Job)
async def get_job(job_id: int, db: Session = Depends(get_db)):
    """Get a specific job by ID."""
    repo = PositionRepository(db)
    position = repo.get_by_id(job_id)
    
    if not position:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Job not found")
    
    return Job.model_validate(position)
