"""Loading task for RQ."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def task_loader():
    """Execute loading process with upsert."""
    from src.etl.load import run_load_process
    
    stats = run_load_process()
    
    return {
        "status": "completed",
        "message": "Loading finished",
        "stats": stats
    }
