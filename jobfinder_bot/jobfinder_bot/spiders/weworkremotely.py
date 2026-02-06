"""Spider for scraping job listings from WeWorkRemotely."""
import scrapy


class WeWorkRemotelySpider(scrapy.Spider):
    """Spider for WeWorkRemotely job board."""
    
    name = "weworkremotely_jobs"
    allowed_domains = ["weworkremotely.com"]

    def start_requests(self):
        """Generate initial requests with search query."""
        search_term = getattr(self, "query", "data+engineer")
        url = f"https://weworkremotely.com/remote-jobs/search?term={search_term}"
        yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        """Parse job listings from search results."""
        # Extract job listings
        job_listings = response.css('.new-listing-container')
        
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
