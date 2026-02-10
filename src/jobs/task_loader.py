"""Loading task for RQ."""
import sys
from pathlib import Path
import shutil

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def task_loader(output_dir=None):
    """Execute loading process with upsert.
    
    This is Step 3 of the pipeline: Scrape → Validate → Load
    
    Args:
        output_dir: Directory containing this pipeline run's validated files
    """
    from src.etl.load import run_load_process
    from src.core.logging import get_logger
    
    logger = get_logger(__name__)
    stats = run_load_process(output_dir=output_dir)
    
    # Clean up processed files after successful load (only if files were processed and no errors)
    if output_dir and stats.get("processed", 0) > 0 and Path(output_dir).exists():
        try:
            # Only clean up if it's a unique run directory (has timestamp subdirectory structure)
            output_path = Path(output_dir)
            # Check if it's a timestamped directory (HHMMSS format - 6 digits)
            if output_path.name.isdigit() and len(output_path.name) == 6:
                logger.info(f"🧹 Cleaning up processed files from {output_dir}")
                shutil.rmtree(output_dir)
                logger.info(f"✅ Cleanup complete")
            else:
                logger.info(f"⏭️  Skipping cleanup (not a timestamped run directory)")
        except Exception as e:
            logger.warning(f"Failed to clean up {output_dir}: {e}")
    
    return {
        "status": "completed",
        "message": "Loading finished",
        "stats": stats
    }
