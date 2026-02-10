"""Cleanup task for RQ - removes JSON files after successful pipeline."""
import sys
import shutil
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def task_cleanup(output_dir=None):
    """Clean up JSON files after successful pipeline completion.
    
    This is Step 4 of the pipeline: Scrape → Validate → Load → Cleanup
    
    Args:
        output_dir: Directory containing this pipeline run's files to clean up
    """
    from src.core.logging import get_logger
    
    logger = get_logger(__name__)
    
    if not output_dir:
        return {
            "status": "skipped",
            "message": "No output directory specified",
            "files_removed": 0
        }
    
    output_path = Path(output_dir)
    
    if not output_path.exists():
        return {
            "status": "skipped",
            "message": f"Output directory does not exist: {output_dir}",
            "files_removed": 0
        }
    
    try:
        # Count files before removal
        json_files = list(output_path.glob("*.json"))
        file_count = len(json_files)
        
        # Remove the entire pipeline directory
        shutil.rmtree(output_path)
        
        logger.info(f"Cleaned up {file_count} JSON files from {output_dir}")
        
        return {
            "status": "completed",
            "message": f"Removed {file_count} files from {output_dir}",
            "files_removed": file_count
        }
    except Exception as e:
        logger.error(f"Error cleaning up {output_dir}: {e}")
        return {
            "status": "error",
            "error": str(e),
            "files_removed": 0
        }
