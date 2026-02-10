"""Job search and listing routes."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from collections import Counter
import re
from src.database.connection import get_db
from src.database.repositories import PositionRepository
from src.database.models import Position
from src.schemas.job import Job, JobList, JobStats, WordFrequencyResponse, WordFrequencyItem

router = APIRouter()


@router.get("/search", response_model=List[Job])
async def search_jobs(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(100, ge=1, le=10000),
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
    source: Optional[str] = None,
    limit: int = Query(100, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List all jobs with optional filters."""
    repo = PositionRepository(db)
    positions = repo.get_all(limit=limit, offset=offset, search=search, company=company, source=source)
    total = repo.count(search=search, company=company, source=source)
    
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


@router.get("/analysis/word-frequency", response_model=WordFrequencyResponse)
async def get_word_frequency(
    top_n: int = Query(20, ge=5, le=100, description="Number of top words to return"),
    min_length: int = Query(3, ge=2, le=10, description="Minimum word length"),
    db: Session = Depends(get_db)
):
    """Get word frequency analysis from job titles.
    
    Returns counts of JOBS (not occurrences) that match each n-gram when searched.
    This aligns with the frontend filtering behavior using substring matching.
    """
    repo = PositionRepository(db)
    
    # Common words to exclude
    stop_words = {
        'the', 'and', 'for', 'with', 'this', 'that', 'from', 'are', 'was', 'were',
        'been', 'being', 'have', 'has', 'had', 'does', 'did', 'can', 'could', 'will',
        'would', 'should', 'may', 'might', 'must', 'our', 'your', 'their'
    }
    
    # First, extract all unique n-grams from job titles
    all_ngrams = set()
    positions = db.query(Position).all()
    
    for pos in positions:
        title = pos.title.lower()
        segments = re.split(r'[,;:()\[\]{}|/\-–—]+', title)
        
        for segment in segments:
            words = re.findall(r'\b[a-z0-9-]+\b', segment.strip())
            
            # Single words
            for word in words:
                if len(word) >= min_length and word not in stop_words:
                    all_ngrams.add(word)
            
            # Two-word phrases (consecutive within same segment)
            for i in range(len(words) - 1):
                if (len(words[i]) >= min_length and words[i] not in stop_words and
                    len(words[i+1]) >= min_length and words[i+1] not in stop_words):
                    phrase = f"{words[i]} {words[i+1]}"
                    all_ngrams.add(phrase)
            
            # Three-word phrases (consecutive within same segment)
            for i in range(len(words) - 2):
                if (len(words[i]) >= min_length and words[i] not in stop_words and
                    len(words[i+1]) >= min_length and words[i+1] not in stop_words and
                    len(words[i+2]) >= min_length and words[i+2] not in stop_words):
                    phrase = f"{words[i]} {words[i+1]} {words[i+2]}"
                    all_ngrams.add(phrase)
    
    # Now count how many jobs match each n-gram using the same search logic as frontend
    ngram_counts = {}
    
    for ngram in all_ngrams:
        # Use repository search to match frontend behavior exactly
        count = repo.count(search=ngram)
        if count > 0:
            ngram_counts[ngram] = count
    
    # Separate by word count
    single_words = {}
    two_word_phrases = {}
    three_word_phrases = {}
    
    for ngram, count in ngram_counts.items():
        word_count = len(ngram.split())
        
        if word_count == 1:
            single_words[ngram] = count
        elif word_count == 2:
            two_word_phrases[ngram] = count
        elif word_count == 3:
            three_word_phrases[ngram] = count
    
    # Sort by count and return top N
    return WordFrequencyResponse(
        single_words=[
            WordFrequencyItem(text=word, count=count) 
            for word, count in sorted(single_words.items(), key=lambda x: x[1], reverse=True)[:top_n]
        ],
        two_word_phrases=[
            WordFrequencyItem(text=phrase, count=count) 
            for phrase, count in sorted(two_word_phrases.items(), key=lambda x: x[1], reverse=True)[:top_n]
        ],
        three_word_phrases=[
            WordFrequencyItem(text=phrase, count=count) 
            for phrase, count in sorted(three_word_phrases.items(), key=lambda x: x[1], reverse=True)[:top_n]
        ]
    )
