"""Sync check task for RQ."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def task_sync_check():
    """Check synchronization status between local JSON and database."""
    from src.etl.load import get_sync_status
    
    result = get_sync_status()
    
    return {
        "status": "completed",
        "message": "Sync check finished",
        "data": result
    }
