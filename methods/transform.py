"""Transform module for parsing and extracting job data from HTML."""
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from utils.logger import get_logger

logger = get_logger(__name__)


class Transform:
    """Handles transformation of raw HTML into structured job data."""
    
    def __init__(self):
        logger.info("Transform initialized")

    def soupHtml(self, html_text: str) -> BeautifulSoup:
        """
        Parse HTML text into BeautifulSoup object.
        
        Args:
            html_text: Raw HTML string
            
        Returns:
            BeautifulSoup object
        """
        try:
            return BeautifulSoup(html_text, "html.parser")
        except Exception as e:
            logger.error(f"Failed to parse HTML: {e}")
            raise

    def getJobs(self, site_source: str, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extract jobs from parsed HTML based on site source.
        
        Args:
            site_source: Name of the site (e.g., 'weworkremotely')
            soup: BeautifulSoup object
            
        Returns:
            List of job dictionaries
        """
        logger.info(f"Extracting jobs from {site_source}")
        
        try:
            match site_source:
                case "weworkremotely":
                    return self.handleWeWorkRemotely(soup)
                case "skipthedrive":
                    return self.handleSkipTheDrive(soup)
                case _:
                    logger.warning(f"Unknown site source: {site_source}")
                    return []
        except Exception as e:
            logger.error(f"Error extracting jobs from {site_source}: {e}", exc_info=True)
            return []

    def handleWeWorkRemotely(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extract jobs from WeWorkRemotely HTML.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        try:
            job_listings = soup.select('.new-listing-container')
            logger.debug(f"Found {len(job_listings)} job listings on WeWorkRemotely")

            for job in job_listings:
                try:
                    title_tag = job.select_one('.new-listing__header__title')
                    company_tag = job.select_one('.new-listing__company-name')
                    location_tag = job.select_one('.new-listing__company-headquarters')
                    salary_tag = job.select('.new-listing__categories__category')

                    # Extract text safely
                    title = title_tag.text.strip() if title_tag else 'N/A'
                    company = company_tag.text.strip() if company_tag else 'N/A'
                    location = location_tag.text.strip() if location_tag else 'N/A'
                    
                    # Extract salary if available
                    salary = 'N/A'
                    if salary_tag and len(salary_tag) > 1:
                        salary = salary_tag[1].text.strip()

                    # Extract links
                    links = [f"https://weworkremotely.com{a['href']}" 
                            for a in job.find_all('a', href=True)]

                    job_data = {
                        'title': title,
                        'company': company,
                        'location': location,
                        'salary': salary,
                        'link': links[0] if links else 'N/A'
                    }
                    
                    jobs.append(job_data)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse individual job from WeWorkRemotely: {e}")
                    continue

            logger.info(f"Successfully extracted {len(jobs)} jobs from WeWorkRemotely")
            
        except Exception as e:
            logger.error(f"Error in handleWeWorkRemotely: {e}", exc_info=True)
        
        return jobs

    def handleSkipTheDrive(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extract jobs from SkipTheDrive HTML.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            List of job dictionaries
        """
        job_posts = []
        
        try:
            articles = soup.select("article.post")
            logger.debug(f"Found {len(articles)} job articles on SkipTheDrive")
        
            for article in articles:
                try:
                    title_element = article.select_one("h2.post-title a")
                    company_element = article.select_one(".custom_fields_company_name_display_search_results")
                    date_element = article.select_one("time.post-date")
                    
                    if title_element and company_element and date_element:
                        job_data = {
                            "title": title_element.text.strip(),
                            "link": title_element.get("href", "N/A"),
                            "company": company_element.text.strip(),
                            "date_posted": date_element.get("datetime", "N/A")
                        }
                        job_posts.append(job_data)
                    else:
                        logger.debug("Skipping article with missing required fields")
                        
                except Exception as e:
                    logger.warning(f"Failed to parse individual job from SkipTheDrive: {e}")
                    continue
            
            logger.info(f"Successfully extracted {len(job_posts)} jobs from SkipTheDrive")
            
        except Exception as e:
            logger.error(f"Error in handleSkipTheDrive: {e}", exc_info=True)
        
        return job_posts

