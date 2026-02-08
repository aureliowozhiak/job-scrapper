"""Pipeline-related schemas."""
from typing import List, Optional
from pydantic import BaseModel


class PipelineRequest(BaseModel):
    """Pipeline execution request."""
    steps: Optional[List[str]] = None  # If None, run all steps
    queries: Optional[List[str]] = None  # Custom queries for scraper


class PipelineResponse(BaseModel):
    """Pipeline execution response."""
    message: str
    job_id: Optional[str] = None
    steps: List[str]
