"""Spider for scraping job listings from Remotive API."""
import scrapy
from datetime import datetime
from typing import Any


class RemotiveSpider(scrapy.Spider):
    name = "remotive_jobs"
    allowed_domains = ["remotive.com"]
    
    def start_requests(self):
        """Start requests with search query parameter."""
        search_term = getattr(self, "query", "data engineer")
        
        # Remotive API endpoint - returns all jobs
        url = "https://remotive.com/api/remote-jobs"
        
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
        """Parse Remotive API response."""
        try:
            import json
            # Decode binary response
            data = json.loads(response.body.decode('utf-8'))
            
            # Get jobs array from response
            jobs = data.get('jobs', [])
            
            self.logger.info(f"Found {len(jobs)} total jobs from Remotive API")
            
            # Filter jobs based on search term
            matched_count = 0
            for job in jobs:
                if self._matches_search(job):
                    matched_count += 1
                    yield self._parse_job(job)
            
            self.logger.info(f"Matched {matched_count} jobs for search: {self.search_term}")
                    
        except Exception as e:
            self.logger.error(f"Error parsing Remotive API: {e}", exc_info=True)

    def _matches_search(self, job: dict) -> bool:
        """Check if job matches search criteria."""
        # Make search more lenient - split terms and search each
        search_terms = [term.strip().lower() for term in self.search_term.split() if term.strip()]
        
        # Search in title, category, tags, and company
        title = str(job.get('title', '')).lower()
        category = str(job.get('category', '')).lower()
        tags = ' '.join(str(tag) for tag in job.get('tags', [])).lower()
        company = str(job.get('company_name', '')).lower()
        description = str(job.get('description', '')).lower()[:1000]  # First 1000 chars only
        
        searchable_text = f"{title} {category} {tags} {company} {description}"
        
        # Match if ANY search term is found (more lenient)
        for term in search_terms:
            if term in searchable_text:
                return True
        return False

    def _parse_job(self, job: dict) -> dict:
        """Extract job information from API response."""
        # Parse publication date
        post_date = None
        if 'publication_date' in job:
            try:
                dt = datetime.fromisoformat(job['publication_date'].replace('Z', '+00:00'))
                post_date = dt.strftime('%Y-%m-%d')
            except Exception:
                post_date = job.get('publication_date', '')
        
        # Map job_type to readable format
        job_type_map = {
            'full_time': 'Full-time',
            'part_time': 'Part-time',
            'contract': 'Contract',
            'freelance': 'Freelance'
        }
        job_type = job_type_map.get(job.get('job_type', ''), job.get('job_type', ''))
        
        return {
            "job_title": job.get('title', ''),
            "company": job.get('company_name', ''),
            "post_date": post_date,
            "location": job.get('candidate_required_location', 'Remote'),
            "category": job.get('category', ''),
            "tags": job.get('tags', []),
            "job_type": job_type,
            "salary": job.get('salary', ''),
            "url": job.get('url', ''),
            "description": job.get('description', '')[:500] if job.get('description') else None,
        }
