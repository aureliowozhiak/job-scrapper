"""Validation task for RQ."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def task_validator():
    """Execute link validation and cleanup."""
    from src.etl.validate import cleanup_invalid_jobs
    
    stats = cleanup_invalid_jobs(batch_size=50)
    
    return {
        "status": "completed",
        "message": f"Validation finished: {stats['removed']} invalid jobs removed",
        "stats": stats
    }
