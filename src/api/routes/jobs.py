"""Public job feed routes."""
import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class JobResult(BaseModel):
    """Job search result."""
    link: str


class JobSearchResponse(BaseModel):
    """Response for job search."""
    query: str
    results: List[str]
    count: int


def search_jobs(word: str, db_path: str = "jobs.db") -> List[str]:
    """
    Search for jobs by keyword in the database.
    
    Args:
        word: The search keyword
        db_path: Path to the SQLite database
    
    Returns:
        List of job links matching the search
    """
    try:
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()
        
        query = "SELECT link FROM positions WHERE UPPER(title) LIKE UPPER(?)"
        cursor.execute(query, (f"%{word}%",))
        
        results = [row[0] for row in cursor.fetchall()]
        
        connection.close()
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/search", response_model=JobSearchResponse)
async def search(
    word: str = Query(..., description="Search keyword for job titles")
):
    """
    Search for jobs by keyword.
    
    This is a public endpoint accessible to all users.
    """
    if not word:
        raise HTTPException(status_code=400, detail="Search keyword is required")
    
    results = search_jobs(word)
    
    return JobSearchResponse(
        query=word,
        results=results,
        count=len(results)
    )
