"""Scraping orchestrator - replaces legacy/app.py."""
from datetime import datetime, timezone
from pathlib import Path
import json
from src.etl.extract import Extract
from src.etl.transform import Transform
from src.etl.utils import Utils
from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

# Site configurations
URLS = {
    "weworkremotely": {
        "url_q": "https://weworkremotely.com/remote-jobs/search?term=",
        "active": 1
    },
    "skipthedrive": {
        "url_q": "https://www.skipthedrive.com/?s=",
        "active": 1
    }
}

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


def run_scraper() -> dict:
    """
    Execute the complete scraping process.
    
    Returns:
        dict: Statistics about the scraping process
    """
    logger.info("=" * 60)
    logger.info("STARTING JOB SCRAPING ETL PROCESS")
    
    # Setup paths
    year = datetime.now(timezone.utc).year
    month = datetime.now(timezone.utc).month
    day = datetime.now(timezone.utc).day
    
    logger.info(f"Date: {year}-{month:02d}-{day:02d}")
    logger.info("=" * 60)
    
    utils = Utils()
    
    # Create directory structure
    path = str(settings.data_lake_path)
    output = str(settings.output_path)
    
    try:
        utils.createDir(f"{path}")
        utils.createDir(f"{path}/{year}")
        utils.createDir(f"{path}/{year}/{month}")
        utils.createDir(f"{path}/{year}/{month}/{day}")
        logger.info("Data lake directory structure created")
    except Exception as e:
        logger.error(f"Failed to create directory structure: {e}")
        raise
    
    # Initialize extractor
    extract = Extract(
        urls=URLS,
        date={"year": year, "month": month, "day": day},
        utils=utils
    )
    
    # Extract data for each query
    logger.info(f"Processing {len(QUERIES)} search queries")
    successful_queries = 0
    
    for idx, query in enumerate(QUERIES, 1):
        logger.info(f"Processing query {idx}/{len(QUERIES)}: '{query}'")
        try:
            if extract.extractData(query=query):
                successful_queries += 1
        except Exception as e:
            logger.error(f"Failed to process query '{query}': {e}", exc_info=True)
    
    logger.info(f"Extraction phase complete: {successful_queries}/{len(QUERIES)} queries successful")
    
    # Transform data
    logger.info("Starting transformation phase")
    transform = Transform()
    
    directories = utils.listDir(f"{path}/{year}/{month}/{day}")
    logger.info(f"Found {len(directories)} site directories to process")
    
    processed_sites = 0
    total_jobs = 0
    
    for directory in directories:
        try:
            logger.info(f"Processing directory: {directory}")
            files = utils.listDir(f"{path}/{year}/{month}/{day}/{directory}")
            jobs = []
            
            for file_name in files:
                try:
                    file_path = f"{path}/{year}/{month}/{day}/{directory}/{file_name}"
                    html_text = utils.loadFile(file_path)
                    soup = transform.soupHtml(html_text)
                    extracted_jobs = transform.getJobs(directory, soup)
                    jobs.append(extracted_jobs)
                    logger.debug(f"Processed file: {file_name}")
                except Exception as e:
                    logger.error(f"Failed to process file {file_name}: {e}")
                    continue
            
            # Create output structure
            utils.createDir(f"{output}")
            utils.createDir(f"{output}/{year}")
            utils.createDir(f"{output}/{year}/{month}")
            utils.createDir(f"{output}/{year}/{month}/{day}")
            
            # Save JSON
            output_file = f"{output}/{year}/{month}/{day}/{directory}.json"
            
            try:
                with open(output_file, 'w', encoding='utf-8') as json_file:
                    json.dump(jobs, json_file, ensure_ascii=False, indent=4)
                
                job_count = sum(len(job_list) for job_list in jobs)
                total_jobs += job_count
                processed_sites += 1
                logger.info(f"Saved {job_count} jobs from {directory} to {output_file}")
                
            except IOError as e:
                logger.error(f"Failed to write output file {output_file}: {e}")
                
        except Exception as e:
            logger.error(f"Failed to process directory {directory}: {e}", exc_info=True)
    
    # Final summary
    stats = {
        "queries_processed": successful_queries,
        "queries_total": len(QUERIES),
        "sites_processed": processed_sites,
        "total_jobs": total_jobs,
        "output_dir": f"{output}/{year}/{month}/{day}/"
    }
    
    logger.info("=" * 60)
    logger.info("ETL PROCESS COMPLETE")
    logger.info(f"Queries processed: {successful_queries}/{len(QUERIES)}")
    logger.info(f"Sites processed: {processed_sites}/{len(directories)}")
    logger.info(f"Total jobs extracted: {total_jobs}")
    logger.info("=" * 60)
    
    return stats


def main():
    """Main entry point for standalone execution."""
    stats = run_scraper()
    print(f"\n✅ ETL process complete!")
    print(f"📊 Queries: {stats['queries_processed']}/{stats['queries_total']} | Sites: {stats['sites_processed']} | Jobs: {stats['total_jobs']}")
    print(f"📁 Output saved to: {stats['output_dir']}")


if __name__ == "__main__":
    main()

