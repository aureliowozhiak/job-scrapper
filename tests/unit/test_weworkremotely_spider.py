"""Unit tests for the WeWorkRemotely spider."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from scrapy.http import HtmlResponse

from src.spiders.jobfinder_bot.spiders.weworkremotely import WeWorkRemotelySpider


class TestWeWorkRemotelySpider:
    """Test cases for WeWorkRemotelySpider."""

    def setup_method(self):
        """Set up test fixtures."""
        self.spider = WeWorkRemotelySpider()

    def test_spider_name(self):
        """Test spider has correct name."""
        assert self.spider.name == "weworkremotely_jobs"

    def test_allowed_domains(self):
        """Test spider has correct allowed domains."""
        assert "weworkremotely.com" in self.spider.allowed_domains

    def test_custom_settings(self):
        """Test spider has correct custom settings."""
        settings = self.spider.custom_settings
        assert settings['DOWNLOAD_DELAY'] == 1
        assert settings['CONCURRENT_REQUESTS_PER_DOMAIN'] == 3
        assert settings['RETRY_TIMES'] == 3

    def test_default_headers(self):
        """Test spider has browser-like headers."""
        headers = self.spider.DEFAULT_HEADERS
        assert 'User-Agent' in headers
        assert 'Chrome' in headers['User-Agent']
        assert 'Accept' in headers
        assert 'Accept-Language' in headers

    def test_parse_job_with_valid_data(self):
        """Test _parse_job extracts job data correctly."""
        html = """
        <div class="new-listing-container">
            <a class="listing-link--unlocked" href="/remote-jobs/test-company-data-engineer">
                <span class="new-listing__header__title">Data Engineer</span>
                <span class="new-listing__company-name">Test Company</span>
                <span class="new-listing__company-headquarters">Remote</span>
                <span class="new-listing__categories__category">Full-Time</span>
            </a>
        </div>
        """
        response = HtmlResponse(
            url="https://weworkremotely.com/remote-jobs/search?term=data+engineer",
            body=html.encode('utf-8'),
            encoding='utf-8'
        )
        job = response.css('.new-listing-container')[0]
        
        result = self.spider._parse_job(job, response)
        
        assert result is not None
        assert result['job_title'] == 'Data Engineer'
        assert result['company'] == 'Test Company'
        assert result['location'] == 'Remote'
        assert result['salary'] == 'Full-Time'
        assert 'test-company-data-engineer' in result['url']

    def test_parse_job_with_missing_title(self):
        """Test _parse_job returns None when title is missing."""
        html = """
        <div class="new-listing-container">
            <a class="listing-link--unlocked" href="/remote-jobs/test">
                <span class="new-listing__company-name">Test Company</span>
            </a>
        </div>
        """
        response = HtmlResponse(
            url="https://weworkremotely.com/remote-jobs/search?term=test",
            body=html.encode('utf-8'),
            encoding='utf-8'
        )
        job = response.css('.new-listing-container')[0]
        
        result = self.spider._parse_job(job, response)
        
        assert result is None

    def test_parse_job_with_missing_company(self):
        """Test _parse_job returns None when company is missing."""
        html = """
        <div class="new-listing-container">
            <a class="listing-link--unlocked" href="/remote-jobs/test">
                <span class="new-listing__header__title">Data Engineer</span>
            </a>
        </div>
        """
        response = HtmlResponse(
            url="https://weworkremotely.com/remote-jobs/search?term=test",
            body=html.encode('utf-8'),
            encoding='utf-8'
        )
        job = response.css('.new-listing-container')[0]
        
        result = self.spider._parse_job(job, response)
        
        assert result is None

    def test_parse_with_multiple_jobs(self):
        """Test parse extracts multiple jobs."""
        html = """
        <div class="new-listing-container">
            <a class="listing-link--unlocked" href="/remote-jobs/job1">
                <span class="new-listing__header__title">Job 1</span>
                <span class="new-listing__company-name">Company 1</span>
            </a>
        </div>
        <div class="new-listing-container">
            <a class="listing-link--unlocked" href="/remote-jobs/job2">
                <span class="new-listing__header__title">Job 2</span>
                <span class="new-listing__company-name">Company 2</span>
            </a>
        </div>
        """
        response = HtmlResponse(
            url="https://weworkremotely.com/remote-jobs/search?term=test",
            body=html.encode('utf-8'),
            encoding='utf-8'
        )
        
        results = list(self.spider.parse(response))
        
        assert len(results) == 2
        assert results[0]['job_title'] == 'Job 1'
        assert results[1]['job_title'] == 'Job 2'

    def test_parse_with_cloudflare_block(self):
        """Test parse returns nothing when Cloudflare blocks."""
        html = "<html><body>Just a moment... Checking your browser</body></html>"
        response = HtmlResponse(
            url="https://weworkremotely.com/remote-jobs/search?term=test",
            body=html.encode('utf-8'),
            encoding='utf-8'
        )
        
        results = list(self.spider.parse(response))
        
        assert len(results) == 0

    def test_parse_with_no_jobs(self):
        """Test parse handles empty results gracefully."""
        html = "<html><body><div>No jobs found</div></body></html>"
        response = HtmlResponse(
            url="https://weworkremotely.com/remote-jobs/search?term=test",
            body=html.encode('utf-8'),
            encoding='utf-8'
        )
        
        results = list(self.spider.parse(response))
        
        assert len(results) == 0

    def test_parse_with_alternative_selectors(self):
        """Test parse uses alternative selectors when primary fails."""
        html = """
        <section class="jobs">
            <article>
                <a href="/remote-jobs/job1">
                    <span class="title">Alt Job</span>
                    <span class="company">Alt Company</span>
                </a>
            </article>
        </section>
        """
        response = HtmlResponse(
            url="https://weworkremotely.com/remote-jobs/search?term=test",
            body=html.encode('utf-8'),
            encoding='utf-8'
        )
        
        results = list(self.spider.parse(response))
        
        assert len(results) == 1
        assert results[0]['job_title'] == 'Alt Job'
        assert results[0]['company'] == 'Alt Company'

    def test_query_parameter(self):
        """Test spider accepts custom query parameter."""
        spider = WeWorkRemotelySpider(query="python developer")
        assert spider.query == "python developer"

    def test_region_parameter(self):
        """Test spider accepts region parameter."""
        spider = WeWorkRemotelySpider(region="north-america")
        assert spider.region == "north-america"

    def test_category_parameter(self):
        """Test spider accepts category parameter."""
        spider = WeWorkRemotelySpider(category="programming")
        assert spider.category == "programming"


class TestWeWorkRemotelySpiderAsync:
    """Test async functionality of WeWorkRemotelySpider."""

    @pytest.mark.asyncio
    async def test_start_builds_correct_url(self):
        """Test start() builds URL with query parameter."""
        spider = WeWorkRemotelySpider(query="machine learning")
        
        with patch('httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "<html><body>No jobs</body></html>"
            mock_client.get.return_value = mock_response
            
            results = []
            async for item in spider.start():
                results.append(item)
            
            # Verify URL was called with correct query
            call_args = mock_client.get.call_args
            assert "machine+learning" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_start_handles_timeout(self):
        """Test start() handles timeout gracefully."""
        import httpx
        spider = WeWorkRemotelySpider()
        
        with patch('httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.TimeoutException("Timeout")
            
            results = []
            async for item in spider.start():
                results.append(item)
            
            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_start_handles_http_error(self):
        """Test start() handles HTTP errors gracefully."""
        import httpx
        spider = WeWorkRemotelySpider()
        
        with patch('httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.HTTPError("HTTP Error")
            
            results = []
            async for item in spider.start():
                results.append(item)
            
            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_start_handles_non_200_status(self):
        """Test start() handles non-200 status codes."""
        spider = WeWorkRemotelySpider()
        
        with patch('httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_client.get.return_value = mock_response
            
            results = []
            async for item in spider.start():
                results.append(item)
            
            assert len(results) == 0
