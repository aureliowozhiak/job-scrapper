"""Scrapy runner that executes spiders programmatically and loads results into database."""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
import subprocess
import tempfile
from src.core.logging import get_logger
from src.database.connection import SessionLocal
from src.database.models import Position
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = get_logger(__name__)

# Search queries for job scraping
QUERIES = [
    "data analytics",
    "data engineer",
    "data scientist",
    "data analyst",
    "machine learning engineer",
    "business intelligence analyst",
    "ETL developer",
    "big data engineer",
    "database administrator",
    "SQL developer",
    "Python developer data",
    "AI engineer",
    "cloud data engineer",
    "data architect",
    "BI developer",
    "data warehouse specialist",
    "analytics engineer",
    "data governance specialist",
    "quantitative analyst",
    "data product manager"
]

# Spider configuration: maps internal IDs to display names and search patterns
SPIDER_CONFIG = {
    "skipthedrive_jobs": {
        "nice_name": "SkipTheDrive",
        "domain": "skipthedrive.com",
        "active": True
    },
    "weworkremotely_jobs": {
        "nice_name": "WeWorkRemotely",
        "domain": "weworkremotely.com",
        "active": True,
        "note": "Uses Playwright for browser automation"
    },
    "remoteok_jobs": {
        "nice_name": "RemoteOK",
        "domain": "remoteok.com",
        "active": True,
        "note": "Uses JSON API"
    },
    "remotive_jobs": {
        "nice_name": "Remotive",
        "domain": "remotive.com",
        "active": True,
        "note": "Uses JSON API"
    }
}

# Derived list of active spiders for the orchestration loop
SPIDERS = [spider_id for spider_id, cfg in SPIDER_CONFIG.items() if cfg.get("active", True)]


def normalize_scrapy_job(job: Dict[str, Any], source: str = "unknown") -> Dict[str, str]:
    """
    Normalize Scrapy job data to database schema format.
    """
    link = job.get("url", "").strip()
    
    # If source is unknown, try to infer it from the domain
    if source == "unknown" and link:
        for spider_id, cfg in SPIDER_CONFIG.items():
            if cfg["domain"] in link.lower():
                source = cfg["nice_name"]
                break

    return {
        "title": job.get("job_title", "").strip(),
        "company": job.get("company", "").strip(),
        "link": link,
        "source": source
    }


def run_scrapy_spider_subprocess(spider_name: str, output_file: str, **kwargs) -> bool:
    """
    Run a Scrapy spider using subprocess with dynamic arguments.
    
    Args:
        spider_name: Name of the spider to run
        output_file: Path to save JSON output
        **kwargs: Arguments to pass to the spider (-a key=value)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        import sys
        import os
        
        # Determine correct Python executable (prefer venv if available)
        python_exe = sys.executable
        venv_python = Path(__file__).parent.parent.parent / ".venv" / "bin" / "python3"
        if venv_python.exists():
            python_exe = str(venv_python)
            logger.debug(f"Using venv Python: {python_exe}")
        
        # Build command - use python -m scrapy instead of scrapy command
        cmd = [python_exe, "-m", "scrapy", "crawl", spider_name]
        
        # Add dynamic arguments
        # Filter out non-spider arguments like 'active'
        spider_args = {k: v for k, v in kwargs.items() if k not in ['active']}
        
        for key, value in spider_args.items():
            if value:
                # Pass the value as-is to the spider
                cmd.extend(["-a", f"{key}={value}"])
        
        cmd.extend([
            "-O", output_file,
            "--loglevel=ERROR"
        ])
        
        logger.info(f"Running spider '{spider_name}' with args: {spider_args}")
        logger.debug(f"Full command: {' '.join(cmd)}")
        logger.debug(f"Output file: {output_file}")
        
        # Get absolute path to spiders directory
        cwd = Path(__file__).parent.parent / "spiders"
        logger.debug(f"Working directory: {cwd}")
        
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=180,
            env=os.environ.copy()  # Pass current environment
        )
        
        logger.debug(f"Return code: {result.returncode}")
        
        if result.returncode == 0:
            # Check if output file was created and has content
            if Path(output_file).exists():
                file_size = Path(output_file).stat().st_size
                logger.debug(f"Output file size: {file_size} bytes")
                if file_size > 10:  # More than just "[]"
                    logger.info(f"Spider '{spider_name}' completed successfully ({file_size} bytes)")
                    return True
                else:
                    logger.warning(f"Spider '{spider_name}' produced empty results (file size: {file_size})")
                    return True  # Not a failure, just no results
            else:
                logger.warning(f"Spider '{spider_name}' did not create output file at: {output_file}")
                return False
        else:
            logger.error(f"Spider failed with return code {result.returncode}")
            if result.stderr:
                logger.error(f"Error output: {result.stderr[:500]}")
            if result.stdout:
                logger.debug(f"Stdout: {result.stdout[:500]}")
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
                        source=job_data.get("source"),
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc)
                    )
                    session.add(position)
                    stats["inserted"] += 1
                    logger.debug(f"Inserted: {title} at {company} (Source: {job_data.get('source')})")
                    
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


def fix_database_sources() -> int:
    """
    Correct any missing 'source' fields based on URL patterns.
    Returns the number of records fixed.
    """
    session = SessionLocal()
    total_fixed = 0
    try:
        for spider_id, cfg in SPIDER_CONFIG.items():
            # Use ilike/contains to match domains case-insensitively just in case
            fixed = session.query(Position).filter(
                (Position.source.is_(None)) | (Position.source == "unknown") | (Position.source == ""),
                Position.link.contains(cfg["domain"])
            ).update({"source": cfg["nice_name"]}, synchronize_session=False)
            total_fixed += fixed
        
        session.commit()
        if total_fixed > 0:
            logger.info(f"Source cleanup complete: Fixed {total_fixed} legacy records.")
        return total_fixed
    except Exception as e:
        logger.error(f"Error during database source cleanup: {e}")
        session.rollback()
        return 0
    finally:
        session.close()


def run_integrated_scraper(config: Optional[Dict[str, Any]] = None, **legacy_kwargs) -> Dict[str, Any]:
    """
    Execute the complete integrated scraping process using Scrapy in parallel.
    """
    logger.info("=" * 60)
    logger.info("STARTING PARALLEL INTEGRATED SCRAPY PROCESS")
    logger.info("=" * 60)
    
    total_jobs_scraped = 0
    total_jobs_loaded = 0
    total_duplicates = 0
    total_errors = 0
    queries_processed = 0
    spiders_stats = {}

    # Backward compatibility: convert legacy single-params to a config
    if not config and (legacy_kwargs.get("query") or legacy_kwargs.get("region")):
        config = {
            "spiders": {
                s: {
                    "queries": [legacy_kwargs.get("query")] if legacy_kwargs.get("query") else QUERIES,
                    "region": legacy_kwargs.get("region")
                } for s in SPIDERS
            }
        }

    # Determine which spiders to run
    active_spiders = SPIDERS
    if config and "spiders" in config:
        active_spiders = list(config["spiders"].keys())
    
    # We will parallelize the scraping phase first, then load the data
    # This avoids SQLite lock contention
    tasks = []
    
    for spider_name in active_spiders:
        if spider_name not in SPIDERS:
            logger.warning(f"Skipping unknown spider: {spider_name}")
            continue

        spider_mission = config["spiders"].get(spider_name, {}) if config else {}
        spider_queries = spider_mission.get("queries") or QUERIES
        spider_params = {k: v for k, v in spider_mission.items() if k != "queries"}
        
        spiders_stats[spider_name] = {
            "jobs_scraped": 0, "jobs_loaded": 0, "duplicates": 0, "errors": 0, "queries": 0
        }

        for query in spider_queries:
            tasks.append({
                "spider": spider_name,
                "query": query,
                "params": {**spider_params, "query": query}
            })

    logger.info(f"Total tasks to execute in parallel: {len(tasks)}")
    
    # Phase 1: Scraping (Parallel)
    # Use ThreadPoolExecutor to run subprocesses concurrently
    def perform_scrape(task):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            temp_output = tmp.name
        
        try:
            success = run_scrapy_spider_subprocess(task["spider"], temp_output, **task["params"])
            if success and Path(temp_output).exists() and Path(temp_output).stat().st_size > 10:
                with open(temp_output, 'r', encoding='utf-8') as f:
                    scraped_jobs = json.load(f)
                return {"task": task, "success": True, "jobs": scraped_jobs}
            else:
                return {"task": task, "success": False, "jobs": []}
        except Exception as e:
            logger.error(f"Scrape task failed for {task['spider']} - {task['query']}: {e}")
            return {"task": task, "success": False, "jobs": [], "error": str(e)}
        finally:
            Path(temp_output).unlink(missing_ok=True)

    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_task = {executor.submit(perform_scrape, task): task for task in tasks}
        for future in as_completed(future_to_task):
            results.append(future.result())

    # Phase 2: Loading (Sequential to avoid DB locks)
    for res in results:
        task = res["task"]
        spider_name = task["spider"]
        
        if not res["success"] or not res["jobs"]:
            if res.get("error"):
                spiders_stats[spider_name]["errors"] += 1
            spiders_stats[spider_name]["queries"] += 1
            continue

        try:
            nice_source = SPIDER_CONFIG.get(spider_name, {}).get("nice_name", spider_name)
            normalized_jobs = [normalize_scrapy_job(job, source=nice_source) for job in res["jobs"]]
            valid_jobs = [j for j in normalized_jobs if j["title"] and j["company"] and j["link"] != "N/A"]
            
            jobs_scraped = len(valid_jobs)
            spiders_stats[spider_name]["jobs_scraped"] += jobs_scraped
            
            if valid_jobs:
                load_stats = load_jobs_to_database(valid_jobs)
                spiders_stats[spider_name]["jobs_loaded"] += load_stats["inserted"]
                spiders_stats[spider_name]["duplicates"] += load_stats["duplicates"]
                spiders_stats[spider_name]["errors"] += load_stats["errors"]
            
            spiders_stats[spider_name]["queries"] += 1
            queries_processed += 1
        except Exception as e:
            logger.error(f"Error loading results for {spider_name}: {e}")
            spiders_stats[spider_name]["errors"] += 1

    # Aggregate stats
    for s_name, s_stats in spiders_stats.items():
        total_jobs_scraped += s_stats["jobs_scraped"]
        total_jobs_loaded += s_stats["jobs_loaded"]
        total_duplicates += s_stats["duplicates"]
        total_errors += s_stats["errors"]

    # Final Step: Self-heal any 'unknown' or missing sources
    # This ensures even skipped duplicates get corrected
    fix_database_sources()

    return {
        "queries_processed": queries_processed,
        "jobs_scraped": total_jobs_scraped,
        "jobs_loaded": total_jobs_loaded,
        "duplicates": total_duplicates,
        "errors": total_errors,
        "spiders": spiders_stats
    }


if __name__ == "__main__":
    stats = run_integrated_scraper()
    print(f"\n✅ Scraping process complete!")
    print(f"📊 Queries: {stats['queries_processed']}/{stats['queries_total']}")
    print(f"🔍 Jobs scraped: {stats['jobs_scraped']}")
    print(f"💾 Jobs loaded: {stats['jobs_loaded']}")
    print(f"🔄 Duplicates: {stats['duplicates']}")
    print(f"❌ Errors: {stats['errors']}")
