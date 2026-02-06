"""Scrapy runner that executes spiders programmatically and loads results into database."""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any
import subprocess
import tempfile
from src.core.logging import get_logger
from src.database.connection import SessionLocal
from src.database.models import Position

logger = get_logger(__name__)

# Search queries for job scraping - limited set for efficiency
QUERIES = [
    "data engineer",
    "data scientist",
]

# Available spiders
SPIDERS = [
    "skipthedrive_jobs",
]


def normalize_scrapy_job(job: Dict[str, Any]) -> Dict[str, str]:
    """
    Normalize Scrapy job data to database schema format.
    
    Scrapy returns: job_title, company, post_date, qualifications, url
    Database expects: title, company, link
    
    Args:
        job: Raw job dict from Scrapy spider
        
    Returns:
        Normalized job dict
    """
    return {
        "title": job.get("job_title", "").strip(),
        "company": job.get("company", "").strip(),
        "link": job.get("url", "").strip()
    }


def run_scrapy_spider_subprocess(spider_name: str, query: str, output_file: str) -> bool:
    """
    Run a Scrapy spider using subprocess.
    
    Args:
        spider_name: Name of the spider to run
        query: Search query parameter
        output_file: Path to save JSON output
        
    Returns:
        True if successful, False otherwise
    """
    try:
        normalized_query = query.replace(" ", "+")
        
        # Run scrapy from jobfinder_bot directory
        cmd = [
            "scrapy", "crawl", spider_name,
            "-a", f"query={normalized_query}",
            "-O", output_file,
            "--loglevel=ERROR"  # Only show errors
        ]
        
        logger.info(f"Running spider '{spider_name}' with query '{query}'")
        
        result = subprocess.run(
            cmd,
            cwd="jobfinder_bot",
            capture_output=True,
            text=True,
            timeout=180  # 3 minute timeout per query (with 3 pages limit)
        )
        
        if result.returncode == 0:
            # Check if output file was created and has content
            if Path(output_file).exists():
                file_size = Path(output_file).stat().st_size
                if file_size > 10:  # More than just "[]"
                    logger.info(f"Spider '{spider_name}' completed successfully ({file_size} bytes)")
                    return True
                else:
                    logger.warning(f"Spider '{spider_name}' produced empty results")
                    return True  # Not a failure, just no results
            else:
                logger.warning(f"Spider '{spider_name}' did not create output file")
                return False
        else:
            logger.error(f"Spider failed with return code {result.returncode}")
            if result.stderr:
                logger.error(f"Error output: {result.stderr[:500]}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"Spider '{spider_name}' timed out after 180 seconds")
        return False
    except Exception as e:
        logger.error(f"Error running spider '{spider_name}': {e}", exc_info=True)
        return False


def load_jobs_to_database(jobs: List[Dict[str, str]]) -> Dict[str, int]:
    """
    Load jobs into the database using SQLAlchemy.
    
    Args:
        jobs: List of normalized job dictionaries
        
    Returns:
        Statistics dict with inserted, duplicates, errors counts
    """
    stats = {
        "processed": 0,
        "inserted": 0,
        "duplicates": 0,
        "errors": 0
    }
    
    session = SessionLocal()
    
    try:
        for job_data in jobs:
            stats["processed"] += 1
            
            try:
                title = job_data.get("title", "").strip()
                link = job_data.get("link", "").strip()
                company = job_data.get("company", "").strip()
                
                # Validate required fields
                if not title or not link or not company or link == "N/A":
                    logger.debug(f"Skipping invalid job: {job_data}")
                    stats["errors"] += 1
                    continue
                
                # Check if job already exists
                existing = session.query(Position).filter_by(link=link).first()
                
                if existing:
                    stats["duplicates"] += 1
                    logger.debug(f"Duplicate job: {title} at {company}")
                else:
                    # Create new position
                    position = Position(
                        title=title,
                        link=link,
                        company=company,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc)
                    )
                    session.add(position)
                    stats["inserted"] += 1
                    logger.debug(f"Inserted: {title} at {company}")
                    
            except Exception as e:
                logger.error(f"Error processing job: {e}")
                stats["errors"] += 1
                session.rollback()
                continue
        
        # Commit all changes
        session.commit()
        logger.info(f"Database load complete: {stats}")
        
    except Exception as e:
        logger.error(f"Database error: {e}", exc_info=True)
        session.rollback()
        raise
    finally:
        session.close()
    
    return stats


def run_integrated_scraper() -> Dict[str, Any]:
    """
    Execute the complete integrated scraping process using Scrapy.
    
    This replaces the old ETL process with a direct Scrapy → Database pipeline.
    
    Returns:
        Statistics about the scraping and loading process
    """
    logger.info("=" * 60)
    logger.info("STARTING INTEGRATED SCRAPY SCRAPING PROCESS")
    logger.info("=" * 60)
    
    total_jobs_scraped = 0
    total_jobs_loaded = 0
    total_duplicates = 0
    total_errors = 0
    queries_processed = 0
    spiders_stats = {}
    
    # Process each spider
    for spider_name in SPIDERS:
        logger.info(f"Processing spider: {spider_name}")
        spider_stats = {
            "jobs_scraped": 0,
            "jobs_loaded": 0,
            "duplicates": 0,
            "errors": 0,
            "queries": 0
        }
        
        # Process each query for this spider
        for idx, query in enumerate(QUERIES, 1):
            logger.info(f"[{spider_name}] Query {idx}/{len(QUERIES)}: '{query}'")
            
            # Create temporary file for this query's results
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
                temp_output = tmp.name
            
            try:
                # Run Scrapy spider
                success = run_scrapy_spider_subprocess(spider_name, query, temp_output)
                
                if not success:
                    logger.warning(f"Failed to scrape '{query}' with {spider_name}")
                    Path(temp_output).unlink(missing_ok=True)
                    continue
                
                # Load and normalize scraped data
                try:
                    if not Path(temp_output).exists() or Path(temp_output).stat().st_size < 10:
                        logger.info(f"No data scraped for '{query}' on {spider_name}")
                        spider_stats["queries"] += 1
                        continue
                    
                    with open(temp_output, 'r', encoding='utf-8') as f:
                        scraped_jobs = json.load(f)
                    
                    if not scraped_jobs:
                        logger.info(f"No jobs found for query '{query}' on {spider_name}")
                        spider_stats["queries"] += 1
                        continue
                    
                    # Normalize job data for database
                    normalized_jobs = [normalize_scrapy_job(job) for job in scraped_jobs]
                    
                    # Filter out invalid jobs
                    valid_jobs = [
                        job for job in normalized_jobs 
                        if job["title"] and job["company"] and job["link"] and job["link"] != "N/A"
                    ]
                    
                    jobs_scraped = len(valid_jobs)
                    spider_stats["jobs_scraped"] += jobs_scraped
                    
                    logger.info(f"Scraped {jobs_scraped} valid jobs for '{query}' from {spider_name}")
                    
                    # Load into database
                    if valid_jobs:
                        load_stats = load_jobs_to_database(valid_jobs)
                        spider_stats["jobs_loaded"] += load_stats["inserted"]
                        spider_stats["duplicates"] += load_stats["duplicates"]
                        spider_stats["errors"] += load_stats["errors"]
                        
                        logger.info(
                            f"Loaded {load_stats['inserted']} new jobs, "
                            f"{load_stats['duplicates']} duplicates, "
                            f"{load_stats['errors']} errors"
                        )
                    
                    spider_stats["queries"] += 1
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON from spider for query '{query}': {e}")
                except Exception as e:
                    logger.error(f"Error processing scraped data for '{query}': {e}", exc_info=True)
                finally:
                    # Clean up temp file
                    Path(temp_output).unlink(missing_ok=True)
                    
            except Exception as e:
                logger.error(f"Unexpected error processing query '{query}' with {spider_name}: {e}", exc_info=True)
        
        # Store spider stats
        spiders_stats[spider_name] = spider_stats
        total_jobs_scraped += spider_stats["jobs_scraped"]
        total_jobs_loaded += spider_stats["jobs_loaded"]
        total_duplicates += spider_stats["duplicates"]
        total_errors += spider_stats["errors"]
        queries_processed += spider_stats["queries"]
        
        logger.info(f"Spider {spider_name} complete: {spider_stats}")
    
    # Final summary
    stats = {
        "queries_processed": queries_processed,
        "queries_total": len(QUERIES) * len(SPIDERS),
        "jobs_scraped": total_jobs_scraped,
        "jobs_loaded": total_jobs_loaded,
        "duplicates": total_duplicates,
        "errors": total_errors,
        "spiders": spiders_stats
    }
    
    logger.info("=" * 60)
    logger.info("INTEGRATED SCRAPING PROCESS COMPLETE")
    logger.info(f"Total queries processed: {queries_processed}/{len(QUERIES) * len(SPIDERS)}")
    logger.info(f"Total jobs scraped: {total_jobs_scraped}")
    logger.info(f"Total jobs loaded (new): {total_jobs_loaded}")
    logger.info(f"Total duplicates skipped: {total_duplicates}")
    logger.info(f"Total errors: {total_errors}")
    logger.info("=" * 60)
    
    return stats


if __name__ == "__main__":
    stats = run_integrated_scraper()
    print(f"\n✅ Scraping process complete!")
    print(f"📊 Queries: {stats['queries_processed']}/{stats['queries_total']}")
    print(f"🔍 Jobs scraped: {stats['jobs_scraped']}")
    print(f"💾 Jobs loaded: {stats['jobs_loaded']}")
    print(f"🔄 Duplicates: {stats['duplicates']}")
    print(f"❌ Errors: {stats['errors']}")
