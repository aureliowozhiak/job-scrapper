"""Scraping task for RQ."""


def task_scraper():
    """Execute integrated scraping process using Scrapy."""
    try:
        from src.etl.scrapy_runner import run_integrated_scraper
        
        stats = run_integrated_scraper()
        
        return {
            "status": "completed",
            "message": "Scraping finished",
            "stats": stats
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

