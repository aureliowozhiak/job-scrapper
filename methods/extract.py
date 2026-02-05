"""Extract module for fetching job listings from configured sites."""
import requests
import time
from typing import Dict, Any
from utils.logger import get_logger

logger = get_logger(__name__)


class Extract:
    """Handles data extraction from job listing websites."""
    
    def __init__(self, urls: Dict[str, Dict[str, Any]], date: Dict[str, int], utils, path: str = "lake"):
        """
        Initialize Extract with configuration.
        
        Args:
            urls: Dictionary of site configurations
            date: Dictionary with year, month, day
            utils: Utils instance for file operations
            path: Base path for data lake
        """
        self.urls = urls
        self.path = path
        self.year = date["year"]
        self.month = date["month"]
        self.day = date["day"]
        self.utils = utils
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        
        logger.info(f"Extract initialized for date: {self.year}/{self.month}/{self.day}")

    def _make_request_with_retry(self, url: str) -> requests.Response:
        """
        Make HTTP request with retry logic.
        
        Args:
            url: URL to fetch
            
        Returns:
            Response object
            
        Raises:
            requests.RequestException: After all retries fail
        """
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Attempting request to {url} (attempt {attempt + 1}/{self.max_retries})")
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                logger.debug(f"Successfully fetched {url}")
                return response
            except requests.Timeout:
                logger.warning(f"Timeout on attempt {attempt + 1} for {url}")
            except requests.ConnectionError:
                logger.warning(f"Connection error on attempt {attempt + 1} for {url}")
            except requests.HTTPError as e:
                logger.error(f"HTTP error {e.response.status_code} for {url}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1} for {url}: {e}")
            
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay * (attempt + 1))
        
        raise requests.RequestException(f"Failed to fetch {url} after {self.max_retries} attempts")

    def extractData(self, query: str = "data engineer") -> bool:
        """
        Extract data for a given query from all active sites.
        
        Args:
            query: Search query string
            
        Returns:
            True if at least one site was successfully scraped
        """
        success_count = 0
        normalized_query = query.replace(" ", "+")
        logger.info(f"Starting extraction for query: '{query}'")
        
        for site, data in self.urls.items():
            if data.get("active") != 1:
                logger.debug(f"Skipping inactive site: {site}")
                continue
            
            try:
                endpoint = data['url_q'] + normalized_query
                logger.info(f"Extracting from {site}: {endpoint}")
                
                # Create directory for this site
                site_dir = f"{self.path}/{self.year}/{self.month}/{self.day}/{site}"
                self.utils.createDir(site_dir)
                
                # Fetch data with retry logic
                html_response = self._make_request_with_retry(endpoint)
                
                if html_response.status_code == 200:
                    file_name_path = f"{site_dir}/{query.replace(' ', '_')}.html"
                    
                    with open(file_name_path, "w", encoding='utf-8') as f:
                        f.write(html_response.text)
                    
                    logger.info(f"Successfully saved data from {site} to {file_name_path}")
                    success_count += 1
                else:
                    logger.warning(f"Unexpected status code {html_response.status_code} from {site}")
                    
            except requests.RequestException as e:
                logger.error(f"Failed to extract from {site} for query '{query}': {e}")
            except IOError as e:
                logger.error(f"Failed to write file for {site}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error extracting from {site}: {e}", exc_info=True)
        
        logger.info(f"Extraction complete: {success_count}/{len([s for s, d in self.urls.items() if d.get('active') == 1])} sites successful")
        return success_count > 0