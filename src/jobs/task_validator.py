"""Validation task for RQ."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def task_validator(output_dir=None):
    """Validate scraped JSON files before loading to database.
    
    This is Step 2 of the pipeline: Scrape → Validate → Load
    
    Args:
        output_dir: Directory containing this pipeline run's scraped files
    """
    from src.etl.validate import validate_scraped_files
    
    # Validate with structure checks only (no link validation for speed)
    stats = validate_scraped_files(output_dir=output_dir, skip_link_validation=True)
    
    return {
        "status": "completed",
        "message": f"Validation finished: {stats['valid_jobs']}/{stats['total_jobs']} valid jobs",
        "stats": stats
    }
