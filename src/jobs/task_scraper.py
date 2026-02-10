"""Scraping task for RQ."""


def task_scraper(query=None, region=None, config=None, output_dir=None):
    """Execute scraping process and save to JSON files (does not load to database).
    
    This is Step 1 of the pipeline: Scrape → Validate → Load
    
    Args:
        output_dir: Unique directory for this pipeline run's output files
    """
    try:
        from src.etl.scrapy_runner import run_scraper_to_files
        
        stats = run_scraper_to_files(config=config, query=query, region=region, output_dir=output_dir)
        
        return {
            "status": "completed",
            "message": f"Scraping finished: {stats['jobs_scraped']} jobs saved to files",
            "stats": stats
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

