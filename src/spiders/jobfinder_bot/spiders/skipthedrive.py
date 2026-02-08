"""Spider for scraping job listings from SkipTheDrive."""
import re
import scrapy


class SkipTheDriveSpider(scrapy.Spider):
    name = "skipthedrive_jobs"
    allowed_domains = ["skipthedrive.com"]

    # Search for 'data engineer'
    search_query = "data+engineer"
    start_urls = [f"https://www.skipthedrive.com/?s={search_query}"]
    
    # Limit pages to scrape
    max_pages = 3  # Only scrape first 3 pages
    pages_crawled = 0

    def start_requests(self):
        search_term = getattr(self, "query", "data+engineer")
        region = getattr(self, "region", None)
        job_type = getattr(self, "job_type", None)
        
        url = f"https://www.skipthedrive.com/?s={search_term}"
        if region:
            url += f"&search_region={region}"
        if job_type:
            url += f"&job_type={job_type}"
            
        self.pages_crawled = 0
        yield scrapy.Request(url=url, callback=self.parse)


    def parse(self, response):
        # Follow all links that match https://www.skipthedrive.com/job/*
        job_links = response.xpath("//a[contains(@href, '/job/')]/@href").getall()

        for link in job_links:
            full_url = response.urljoin(link)
            if re.match(r"https://www\.skipthedrive\.com/job/.+", full_url):
                yield scrapy.Request(full_url, callback=self.parse_job)

        # Pagination logic with limit
        self.pages_crawled += 1
        
        if self.pages_crawled >= self.max_pages:
            self.logger.info(f"Reached max pages limit ({self.max_pages})")
            return
        
        current_page = int(response.url.split("/page/")[1].split("/")[0]) if "/page/" in response.url else 1
        search_term = getattr(self, "query", "data+engineer")
        region = getattr(self, "region", None)
        job_type = getattr(self, "job_type", None)
        
        next_page = current_page + 1
        next_page_url = f"https://www.skipthedrive.com/page/{next_page}/?s={search_term}"
        if region:
            next_page_url += f"&search_region={region}"
        if job_type:
            next_page_url += f"&job_type={job_type}"

        # Check if there are job links on the current page to decide if we should continue
        if job_links:
            yield scrapy.Request(next_page_url, callback=self.parse)

    def parse_job(self, response):
        company = response.xpath("//div[@class='custom_fields_company_name_display']/text()").getall()
        company = company[-1].replace('-', '').strip() if isinstance(company, list) else company

        post_date = response.xpath("//div[@class='custom_fields_job_date_display']/text()").getall()
        post_date = post_date[-1].replace('-', '').strip() if isinstance(post_date, list) else post_date

        qualifications = response.xpath("(.//*[self::h2 or self::strong][contains(., 'Qualifications')])/following::ul[1]/li/text()").getall()
        if qualifications:
            qualifications = [q.strip() for q in qualifications if q.strip()]

        yield {
            "job_title": response.xpath("//h1/text()").get(),
            "company": company,
            "post_date": post_date,
            "qualifications": qualifications,
            "url": response.url
        }
