"""Job-related Pydantic schemas."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, HttpUrl, Field


class JobBase(BaseModel):
    """Base job schema."""
    title: str = Field(..., min_length=1, max_length=500)
    link: str = Field(..., min_length=1, max_length=1000)
    company: str = Field(..., min_length=1, max_length=200)


class JobCreate(JobBase):
    """Schema for creating a new job."""
    pass


class JobSchema(JobBase):
    """Complete job schema with database fields."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}


class JobSearchRequest(BaseModel):
    """Job search request schema."""
    query: str = Field(..., min_length=1, description="Search term")
    company: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class JobSearchResponse(BaseModel):
    """Job search response schema."""
    jobs: List[JobSchema]
    total: int
    count: int
    query: Optional[str] = None


class JobList(BaseModel):
    """List of jobs with pagination info."""
    jobs: List[JobSchema]
    total: int
    count: int
    limit: int = 100
    offset: int = 0


class JobStats(BaseModel):
    """Database statistics."""
    total_jobs: int
    total_companies: int
    last_updated: Optional[datetime] = None


# Aliases for backward compatibility
Job = JobSchema
