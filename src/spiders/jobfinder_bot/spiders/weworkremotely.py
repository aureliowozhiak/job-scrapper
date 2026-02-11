"""Spider for scraping job listings from WeWorkRemotely."""
import scrapy
from scrapy.http import HtmlResponse
import httpx


class WeWorkRemotelySpider(scrapy.Spider):
    """Spider for WeWorkRemotely job board.
    
    Uses httpx async client for HTTP calls to avoid Scrapy fingerprinting
    and enable concurrent requests, then parses with Scrapy selectors.
    """
    
    name = "weworkremotely_jobs"
    allowed_domains = ["weworkremotely.com"]
    
    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 3,
        'RETRY_TIMES': 3,
    }
    
    # Default headers to mimic browser
    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    async def start(self):
        """Generate initial requests with search query and filters (async)."""
        search_term = getattr(self, "query", "data+engineer")
        region = getattr(self, "region", None)
        category = getattr(self, "category", None)
        
        # URL encode spaces as + for search term
        search_term = search_term.replace(" ", "+")
        url = f"https://weworkremotely.com/remote-jobs/search?term={search_term}"
        
        if region:
            url += f"&region[]={region}"
        if category:
            url += f"&category[]={category}"
        
        self.logger.info(f"Starting async request to: {url}")
        
        # Use httpx async client to fetch the page
        async with httpx.AsyncClient(headers=self.DEFAULT_HEADERS, timeout=30.0) as client:
            try:
                resp = await client.get(url)
                self.logger.info(f"Response status: {resp.status_code}, length: {len(resp.text)}")
                
                if resp.status_code == 200:
                    # Create a Scrapy response from httpx response
                    response = HtmlResponse(
                        url=url,
                        body=resp.text.encode('utf-8'),
                        encoding='utf-8'
                    )
                    for item in self.parse(response):
                        yield item
                else:
                    self.logger.error(f"Request failed with status {resp.status_code}")
            except httpx.TimeoutException as e:
                self.logger.error(f"Request timed out: {e}")
            except httpx.HTTPError as e:
                self.logger.error(f"HTTP error: {e}")
            except Exception as e:
                self.logger.error(f"Request failed: {e}")

    def parse(self, response):
        """Parse job listings from search results."""
        self.logger.info(f"Parse called, response length: {len(response.body)}")
        
        # Check for Cloudflare block
        if 'Just a moment' in response.text or 'Checking your browser' in response.text:
            self.logger.warning("Cloudflare challenge detected - cannot proceed without JavaScript")
            return
        
        # Try multiple selectors for job listings (site structure may vary)
        job_listings = response.css('.new-listing-container')
        
        if not job_listings:
            job_listings = response.css('section.jobs article')
        
        if not job_listings:
            job_listings = response.css('.jobs-container article')
        
        if not job_listings:
            job_listings = response.css('li.feature')
            
        self.logger.info(f"Found {len(job_listings)} job listings")
        
        if not job_listings:
            self.logger.warning("No job listings found. Page structure may have changed.")
            self.logger.warning(f"Response body length: {len(response.body)}")
            self.logger.debug(f"Response preview: {response.text[:500]}")
            return
        
        for job in job_listings:
            item = self._parse_job(job, response)
            if item:
                yield item
    
    def _parse_job(self, job, response):
        """Extract job data from a single listing element."""
        try:
            # Try multiple selectors for each field
            title = (
                job.css('.new-listing__header__title::text').get() or
                job.css('.title::text').get() or
                job.css('h2::text').get() or
                job.css('span.title::text').get()
            )
            
            company = (
                job.css('.new-listing__company-name::text').get() or
                job.css('.company::text').get() or
                job.css('span.company::text').get()
            )
            
            location = (
                job.css('.new-listing__company-headquarters::text').get() or
                job.css('.region::text').get() or
                job.css('span.region::text').get()
            )
            
            # Get job URL
            job_url = (
                job.css('a.listing-link--unlocked::attr(href)').get() or
                job.css('a.listing-link::attr(href)').get() or
                job.css('a::attr(href)').get()
            )
            
            if title and company and job_url:
                full_url = response.urljoin(job_url)
                
                # Extract additional info
                categories = job.css('.new-listing__categories__category::text').getall()
                employment_type = categories[0].strip() if len(categories) > 0 else None
                
                return {
                    "job_title": title.strip() if title else "N/A",
                    "company": company.strip() if company else "N/A",
                    "post_date": None,
                    "location": location.strip() if location else "N/A",
                    "salary": employment_type,
                    "qualifications": [],
                    "url": full_url
                }
        except Exception as e:
            self.logger.warning(f"Error parsing job listing: {e}")
        return None
