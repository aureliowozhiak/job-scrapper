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
    
    After successful load, cleans up old scraper JSON files (keeping only validated_jobs_*.json)
    
    Args:
        output_dir: Directory containing this pipeline run's validated files
    """
    from src.etl.load import run_load_process
    from src.core.logging import get_logger
    
    logger = get_logger(__name__)
    stats = run_load_process(output_dir=output_dir)
    
    # Clean up old scraper files after successful load (keep validated files for audit)
    if output_dir and stats.get("processed", 0) > 0 and Path(output_dir).exists():
        try:
            output_path = Path(output_dir)
            
            # Remove old scraper files (skipthedrive_*, remoteok_*, etc.)
            # But keep validated_jobs_*.json for audit trail
            scraped_files = [
                f for f in output_path.glob("*.json") 
                if not f.name.startswith("validated_jobs_")
            ]
            
            if scraped_files:
                logger.info(f"🧹 Cleaning up {len(scraped_files)} old scraper files from {output_dir}")
                for file in scraped_files:
                    file.unlink()
                logger.info(f"✅ Cleanup complete (kept validated files for audit)")
            else:
                logger.info(f"⏭️  No old scraper files to clean up")
                
        except Exception as e:
            logger.warning(f"Failed to clean up {output_dir}: {e}")
    
    return {
        "status": "completed",
        "message": "Loading finished",
        "stats": stats
    }
