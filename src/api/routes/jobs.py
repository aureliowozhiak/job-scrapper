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
    ngram_type: Optional[str] = Query(None, regex="^(1|2|3|all)$", description="N-gram type filter: 1, 2, 3, or all"),
    source: Optional[str] = Query(None, description="Filter by job source (e.g., 'SkipTheDrive')"),
    date_from: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """Get word frequency analysis from job titles with compound filters.
    
    Returns counts of JOBS (not occurrences) where each n-gram appears in the title.
    Only analyzes job titles (not company names or sources).
    Each count represents how many job listings contain that word/phrase in their title.
    
    Filters:
    - ngram_type: '1' (single words), '2' (two-word phrases), '3' (three-word phrases), 'all' (default)
    - source: Filter by job board source
    - date_from/date_to: Filter by creation date range
    """
    from datetime import datetime as dt
    
    # Build base query with filters
    query = db.query(Position)
    
    if source:
        query = query.filter(Position.source.ilike(f"%{source}%"))
    
    if date_from:
        try:
            date_from_obj = dt.fromisoformat(date_from.replace('Z', '+00:00'))
            query = query.filter(Position.created_at >= date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = dt.fromisoformat(date_to.replace('Z', '+00:00'))
            query = query.filter(Position.created_at <= date_to_obj)
        except ValueError:
            pass
    
    positions = query.all()
    
    # Common words to exclude
    stop_words = {
        'the', 'and', 'for', 'with', 'this', 'that', 'from', 'are', 'was', 'were',
        'been', 'being', 'have', 'has', 'had', 'does', 'did', 'can', 'could', 'will',
        'would', 'should', 'may', 'might', 'must', 'our', 'your', 'their'
    }
    
    # Determine which n-gram types to process
    process_1gram = ngram_type in (None, 'all', '1')
    process_2gram = ngram_type in (None, 'all', '2')
    process_3gram = ngram_type in (None, 'all', '3')
    
    # Extract all unique n-grams from job titles
    all_ngrams = set()
    
    for pos in positions:
        title = pos.title.lower()
        segments = re.split(r'[,;:()\[\]{}|/\-–—]+', title)
        
        for segment in segments:
            words = re.findall(r'\b[a-z0-9-]+\b', segment.strip())
            
            # Single words
            if process_1gram:
                for word in words:
                    if len(word) >= min_length and word not in stop_words:
                        all_ngrams.add(('1', word))
            
            # Two-word phrases (consecutive within same segment)
            if process_2gram:
                for i in range(len(words) - 1):
                    if (len(words[i]) >= min_length and words[i] not in stop_words and
                        len(words[i+1]) >= min_length and words[i+1] not in stop_words):
                        phrase = f"{words[i]} {words[i+1]}"
                        all_ngrams.add(('2', phrase))
            
            # Three-word phrases (consecutive within same segment)
            if process_3gram:
                for i in range(len(words) - 2):
                    if (len(words[i]) >= min_length and words[i] not in stop_words and
                        len(words[i+1]) >= min_length and words[i+1] not in stop_words and
                        len(words[i+2]) >= min_length and words[i+2] not in stop_words):
                        phrase = f"{words[i]} {words[i+1]} {words[i+2]}"
                        all_ngrams.add(('3', phrase))
    
    # Count jobs matching each n-gram using Python regex for word boundary matching
    # This is more accurate than SQL LIKE which matches substrings
    ngram_counts = {}
    
    # Fetch all filtered positions once (more efficient than N queries)
    filtered_positions = positions  # Already filtered by source/date above
    
    for ngram_type_str, ngram in all_ngrams:
        # Use word boundary regex for accurate matching
        # Pattern matches the ngram as complete word(s), not as substring
        # Escaping special regex chars in the ngram
        escaped_ngram = re.escape(ngram)
        # \b = word boundary, handles start/end of string and punctuation
        pattern = re.compile(rf'\b{escaped_ngram}\b', re.IGNORECASE)
        
        count = sum(1 for pos in filtered_positions if pattern.search(pos.title))
        if count > 0:
            ngram_counts[(ngram_type_str, ngram)] = count
    
    # Separate by word count
    single_words = {}
    two_word_phrases = {}
    three_word_phrases = {}
    
    for (ngram_type_str, ngram), count in ngram_counts.items():
        if ngram_type_str == '1':
            single_words[ngram] = count
        elif ngram_type_str == '2':
            two_word_phrases[ngram] = count
        elif ngram_type_str == '3':
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
