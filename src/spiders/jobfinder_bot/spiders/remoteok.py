"""Spider for scraping job listings from RemoteOK API."""
import scrapy
from datetime import datetime
from typing import Any


class RemoteOKSpider(scrapy.Spider):
    name = "remoteok_jobs"
    allowed_domains = ["remoteok.com"]
    
    def start_requests(self):
        """Start requests with search query parameter."""
        search_term = getattr(self, "query", "data engineer")
        
        # RemoteOK API endpoint - returns all jobs
        url = "https://remoteok.com/api"
        
        # Store search term for filtering
        self.search_term = search_term.lower()
        
        yield scrapy.Request(
            url=url,
            callback=self.parse,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )

    def parse(self, response):
        """Parse RemoteOK API response."""
        try:
            import json
            # Decode binary response
            data = json.loads(response.body.decode('utf-8'))
            
            # First item is metadata, skip it
            if len(data) > 0 and isinstance(data[0], dict) and 'legal' in data[0]:
                data = data[1:]
            
            self.logger.info(f"Found {len(data)} total jobs from RemoteOK API")
            
            # Filter jobs based on search term
            matched_count = 0
            for job in data:
                if self._matches_search(job):
                    matched_count += 1
                    yield self._parse_job(job)
            
            self.logger.info(f"Matched {matched_count} jobs for search: {self.search_term}")
                    
        except Exception as e:
            self.logger.error(f"Error parsing RemoteOK API: {e}", exc_info=True)

    def _matches_search(self, job: dict) -> bool:
        """Check if job matches search criteria."""
        # Make search more lenient - split terms and search each
        search_terms = [term.strip().lower() for term in self.search_term.split() if term.strip()]
        
        # Search in position, tags, and company
        position = str(job.get('position', '')).lower()
        tags = ' '.join(str(tag) for tag in job.get('tags', [])).lower()
        company = str(job.get('company', '')).lower()
        description = str(job.get('description', '')).lower()[:1000]  # First 1000 chars only
        
        searchable_text = f"{position} {tags} {company} {description}"
        
        # Match if ANY search term is found (more lenient)
        for term in search_terms:
            if term in searchable_text:
                return True
        return False

    def _parse_job(self, job: dict) -> dict:
        """Extract job information from API response."""
        # Parse date from epoch timestamp
        post_date = None
        if 'epoch' in job:
            try:
                post_date = datetime.fromtimestamp(job['epoch']).strftime('%Y-%m-%d')
            except Exception:
                post_date = job.get('date', '')
        
        # Extract salary information
        salary_min = job.get('salary_min', 0)
        salary_max = job.get('salary_max', 0)
        salary = None
        if salary_min or salary_max:
            if salary_min and salary_max:
                salary = f"${salary_min:,} - ${salary_max:,}"
            elif salary_min:
                salary = f"${salary_min:,}+"
            elif salary_max:
                salary = f"Up to ${salary_max:,}"
        
        return {
            "job_title": job.get('position', ''),
            "company": job.get('company', ''),
            "post_date": post_date,
            "location": job.get('location', 'Remote'),
            "tags": job.get('tags', []),
            "salary": salary,
            "url": job.get('url', ''),
            "apply_url": job.get('apply_url', ''),
            "description": job.get('description', '')[:500] if job.get('description') else None,
        }
