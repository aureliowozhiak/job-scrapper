"""Spider for scraping job listings from WeWorkRemotely."""
import scrapy


class WeWorkRemotelySpider(scrapy.Spider):
    """Spider for WeWorkRemotely job board with Playwright support.
    
    Uses scrapy-playwright to bypass Cloudflare protection and render JavaScript.
    """
    
    name = "weworkremotely_jobs"
    allowed_domains = ["weworkremotely.com"]
    
    custom_settings = {
        'DOWNLOAD_DELAY': 3,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'RETRY_TIMES': 3,
        'HTTPERROR_ALLOW_ALL': True,
        'DOWNLOAD_HANDLERS': {
            'https': 'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler',
            'http': 'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler',
        },
        'PLAYWRIGHT_BROWSER_TYPE': 'chromium',
        'PLAYWRIGHT_LAUNCH_OPTIONS': {
            'headless': True,
            'timeout': 30000,
        },
        'PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT': 30000,
    }

    def start_requests(self):
        """Generate initial requests with search query and filters using Playwright."""
        search_term = getattr(self, "query", "data+engineer")
        region = getattr(self, "region", None)
        category = getattr(self, "category", None)
        
        url = f"https://weworkremotely.com/remote-jobs/search?term={search_term}"
        
        if region:
            url += f"&region[]={region}"
        if category:
            url += f"&category[]={category}"
            
        yield scrapy.Request(
            url=url, 
            callback=self.parse,
            meta={
                'playwright': True,
                'playwright_include_page': True,
                'playwright_page_goto_kwargs': {
                    'wait_until': 'networkidle',
                    'timeout': 30000,
                }
            },
            errback=self.errback,
            dont_filter=True
        )

    async def parse(self, response):
        """Parse job listings from search results rendered by Playwright."""
        # Close Playwright page after content is loaded
        page = response.meta.get('playwright_page')
        if page:
            await page.close()
        
        if response.status != 200:
            self.logger.error(f"Unexpected status code: {response.status}")
            return
        
        # Extract job listings
        job_listings = response.css('.new-listing-container')
        
        if not job_listings:
            self.logger.warning("No job listings found. Page structure may have changed or Cloudflare is blocking.")
            return
        
        for job in job_listings:
            try:
                # Extract basic info from listing card
                title = job.css('.new-listing__header__title::text').get()
                company = job.css('.new-listing__company-name::text').get()
                location = job.css('.new-listing__company-headquarters::text').get()
                
                # Get job URL
                job_url = job.css('a.new-listing__title__job::attr(href)').get()
                
                if title and company and job_url:
                    full_url = response.urljoin(job_url)
                    
                    # Extract salary if available
                    categories = job.css('.new-listing__categories__category::text').getall()
                    salary = categories[1] if len(categories) > 1 else None
                    
                    yield {
                        "job_title": title.strip() if title else "N/A",
                        "company": company.strip() if company else "N/A",
                        "post_date": None,  # WeWorkRemotely doesn't show dates in search
                        "location": location.strip() if location else "N/A",
                        "salary": salary.strip() if salary else None,
                        "qualifications": [],
                        "url": full_url
                    }
            except Exception as e:
                self.logger.warning(f"Error parsing job listing: {e}")
                continue
        
        # Note: WeWorkRemotely search doesn't have traditional pagination
        # All results appear on one page
    
    async def errback(self, failure):
        """Handle request errors."""
        page = failure.request.meta.get('playwright_page')
        if page:
            await page.close()
        self.logger.error(f"Request failed: {failure}")
