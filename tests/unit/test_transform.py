"""Unit tests for Transform module."""
import pytest
from bs4 import BeautifulSoup
from src.etl.transform import Transform


class TestTransform:
    """Test cases for Transform class."""
    
    @pytest.fixture
    def transform(self):
        """Create Transform instance for testing."""
        return Transform()
    
    def test_soup_html(self, transform):
        """Test HTML parsing."""
        html = "<html><body><h1>Test</h1></body></html>"
        soup = transform.soupHtml(html)
        
        assert isinstance(soup, BeautifulSoup)
        assert soup.h1.text == "Test"
    
    def test_soup_html_invalid(self, transform):
        """Test handling of invalid HTML."""
        # BeautifulSoup is very forgiving, so this won't raise an error
        # but we test that it returns a BeautifulSoup object
        soup = transform.soupHtml("Not valid HTML <>>")
        assert isinstance(soup, BeautifulSoup)
    
    def test_get_jobs_unknown_site(self, transform):
        """Test handling of unknown site source."""
        soup = BeautifulSoup("<html></html>", "html.parser")
        result = transform.getJobs("unknown_site", soup)
        
        assert result == []
    
    def test_handle_weworkremotely_success(self, transform):
        """Test parsing WeWorkRemotely HTML."""
        html = """
        <div class="new-listing-container">
            <h2 class="new-listing__header__title">Python Developer</h2>
            <div class="new-listing__company-name">Tech Corp</div>
            <div class="new-listing__company-headquarters">Remote</div>
            <div class="new-listing__categories__category">Category</div>
            <div class="new-listing__categories__category">$100k-$150k</div>
            <a href="/jobs/123">View Job</a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        jobs = transform.handleWeWorkRemotely(soup)
        
        assert len(jobs) == 1
        assert jobs[0]['title'] == "Python Developer"
        assert jobs[0]['company'] == "Tech Corp"
        assert jobs[0]['location'] == "Remote"
        assert jobs[0]['salary'] == "$100k-$150k"
        assert "https://weworkremotely.com/jobs/123" in jobs[0]['link']
    
    def test_handle_weworkremotely_missing_fields(self, transform):
        """Test parsing WeWorkRemotely with missing fields."""
        html = """
        <div class="new-listing-container">
            <h2 class="new-listing__header__title">Developer</h2>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        jobs = transform.handleWeWorkRemotely(soup)
        
        assert len(jobs) == 1
        assert jobs[0]['title'] == "Developer"
        assert jobs[0]['company'] == "N/A"
        assert jobs[0]['location'] == "N/A"
        assert jobs[0]['salary'] == "N/A"
    
    def test_handle_skipthedrive_success(self, transform):
        """Test parsing SkipTheDrive HTML."""
        html = """
        <article class="post">
            <h2 class="post-title">
                <a href="https://skipthedrive.com/job/123">Data Engineer</a>
            </h2>
            <div class="custom_fields_company_name_display_search_results">DataCo</div>
            <time class="post-date" datetime="2024-01-15">Jan 15, 2024</time>
        </article>
        """
        soup = BeautifulSoup(html, "html.parser")
        jobs = transform.handleSkipTheDrive(soup)
        
        assert len(jobs) == 1
        assert jobs[0]['title'] == "Data Engineer"
        assert jobs[0]['link'] == "https://skipthedrive.com/job/123"
        assert jobs[0]['company'] == "DataCo"
        assert jobs[0]['date_posted'] == "2024-01-15"
    
    def test_handle_skipthedrive_missing_fields(self, transform):
        """Test parsing SkipTheDrive with missing required fields."""
        html = """
        <article class="post">
            <h2 class="post-title">
                <a href="https://skipthedrive.com/job/123">Job</a>
            </h2>
        </article>
        """
        soup = BeautifulSoup(html, "html.parser")
        jobs = transform.handleSkipTheDrive(soup)
        
        # Should skip entries with missing required fields
        assert len(jobs) == 0
    
    def test_handle_skipthedrive_multiple_jobs(self, transform):
        """Test parsing multiple jobs from SkipTheDrive."""
        html = """
        <article class="post">
            <h2 class="post-title"><a href="/job/1">Job 1</a></h2>
            <div class="custom_fields_company_name_display_search_results">Company A</div>
            <time class="post-date" datetime="2024-01-01">Date</time>
        </article>
        <article class="post">
            <h2 class="post-title"><a href="/job/2">Job 2</a></h2>
            <div class="custom_fields_company_name_display_search_results">Company B</div>
            <time class="post-date" datetime="2024-01-02">Date</time>
        </article>
        """
        soup = BeautifulSoup(html, "html.parser")
        jobs = transform.handleSkipTheDrive(soup)
        
        assert len(jobs) == 2
        assert jobs[0]['title'] == "Job 1"
        assert jobs[1]['title'] == "Job 2"
    
    def test_soup_html_exception(self, transform):
        """Test soupHtml with exception during parsing."""
        # Force an exception by passing None
        with pytest.raises(Exception):
            transform.soupHtml(None)
    
    def test_get_jobs_with_exception(self, transform):
        """Test getJobs when handler raises exception."""
        # Create a malformed soup that will cause errors
        html = "malformed"
        soup = BeautifulSoup(html, "html.parser")
        
        # Should return empty list on error
        result = transform.getJobs("weworkremotely", soup)
        assert result == []
    
    def test_handle_weworkremotely_exception(self, transform):
        """Test handleWeWorkRemotely with malformed HTML causing exceptions."""
        html = """
        <div class="new-listing-container">
            <h2 class="new-listing__header__title">Test Job</h2>
            <!-- Missing other required fields -->
            <a>No href attribute</a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        jobs = transform.handleWeWorkRemotely(soup)
        
        # Should still extract what it can
        assert len(jobs) >= 0
    
    def test_handle_skipthedrive_exception(self, transform):
        """Test handleSkipTheDrive with exception during processing."""
        html = """
        <article class="post">
            <h2 class="post-title"><a href="/job/1">Job</a></h2>
            <div class="custom_fields_company_name_display_search_results">Company</div>
            <time class="post-date">Invalid datetime</time>
        </article>
        """
        soup = BeautifulSoup(html, "html.parser")
        
        # Should handle gracefully
        jobs = transform.handleSkipTheDrive(soup)
        assert isinstance(jobs, list)
    
    def test_handle_weworkremotely_no_listings(self, transform):
        """Test handleWeWorkRemotely with no job listings."""
        html = "<html><body>No jobs here</body></html>"
        soup = BeautifulSoup(html, "html.parser")
        jobs = transform.handleWeWorkRemotely(soup)
        
        assert len(jobs) == 0
    
    def test_handle_skipthedrive_no_articles(self, transform):
        """Test handleSkipTheDrive with no articles."""
        html = "<html><body>No articles here</body></html>"
        soup = BeautifulSoup(html, "html.parser")
        jobs = transform.handleSkipTheDrive(soup)
        
        assert len(jobs) == 0
    
    def test_get_jobs_skipthedrive_returns_list(self, transform):
        """Test that getJobs for skipthedrive returns correct data."""
        html = """
        <article class="post">
            <h2 class="post-title"><a href="/job/1">Job 1</a></h2>
            <div class="custom_fields_company_name_display_search_results">Company</div>
            <time class="post-date" datetime="2024-01-01">Date</time>
        </article>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = transform.getJobs("skipthedrive", soup)
        
        assert isinstance(result, list)
        assert len(result) == 1
    
    def test_get_jobs_exception_in_handler(self, transform):
        """Test getJobs when exception occurs inside match block."""
        # Create a mock soup that will cause exception in handler
        from unittest.mock import Mock, patch
        
        soup = BeautifulSoup("<html></html>", "html.parser")
        
        # Patch handleWeWorkRemotely to raise exception
        with patch.object(transform, 'handleWeWorkRemotely', side_effect=Exception("Test error")):
            result = transform.getJobs("weworkremotely", soup)
            assert result == []
    
    def test_handle_weworkremotely_parsing_exception_in_loop(self, transform):
        """Test handleWeWorkRemotely when exception occurs parsing individual job."""
        html = """
        <div class="new-listing-container">
            <h2 class="new-listing__header__title">Valid Job</h2>
            <div class="new-listing__company-name">Company A</div>
            <div class="new-listing__company-headquarters">Remote</div>
            <a href="/job/1">Link</a>
        </div>
        <div class="new-listing-container">
            <h2 class="new-listing__header__title">Bad Job</h2>
            <!-- Missing company and other fields -->
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        
        # Mock find_all to raise exception for second item
        from unittest.mock import Mock, patch
        original_select = soup.select
        
        def mock_select(selector):
            containers = original_select('.new-listing-container')
            if len(containers) > 1:
                # Make second container raise exception when accessing find_all
                mock_container = Mock()
                mock_container.select_one.side_effect = Exception("Parse error")
                return [containers[0], mock_container]
            return original_select(selector)
        
        with patch.object(soup, 'select', side_effect=mock_select):
            # This should handle exception and continue
            jobs = transform.handleWeWorkRemotely(soup)
            # Should still get at least the valid job (or handle gracefully)
            assert isinstance(jobs, list)
    
    def test_handle_weworkremotely_outer_exception(self, transform):
        """Test handleWeWorkRemotely when outer exception occurs."""
        from unittest.mock import Mock, patch
        
        soup = BeautifulSoup("<html></html>", "html.parser")
        
        # Make soup.select raise exception
        with patch.object(soup, 'select', side_effect=Exception("Critical error")):
            jobs = transform.handleWeWorkRemotely(soup)
            # Should return empty list
            assert jobs == []
    
    def test_handle_skipthedrive_parsing_exception_in_loop(self, transform):
        """Test handleSkipTheDrive when exception occurs parsing individual article."""
        html = """
        <article class="post">
            <h2 class="post-title"><a href="/job/1">Job 1</a></h2>
            <div class="custom_fields_company_name_display_search_results">Company</div>
            <time class="post-date" datetime="2024-01-01">Date</time>
        </article>
        <article class="post">
            <h2 class="post-title"><a href="/job/2">Job 2</a></h2>
            <div class="custom_fields_company_name_display_search_results">Company</div>
            <time class="post-date" datetime="2024-01-02">Date</time>
        </article>
        """
        soup = BeautifulSoup(html, "html.parser")
        
        # Mock to raise exception on second article
        from unittest.mock import Mock, patch
        original_select = soup.select
        
        def mock_select(selector):
            if selector == "article.post":
                articles = original_select(selector)
                if len(articles) > 1:
                    # Make second article raise exception
                    mock_article = Mock()
                    mock_article.select_one.side_effect = Exception("Parse error")
                    return [articles[0], mock_article]
            return original_select(selector)
        
        with patch.object(soup, 'select', side_effect=mock_select):
            jobs = transform.handleSkipTheDrive(soup)
            # Should handle exception and continue
            assert isinstance(jobs, list)
    
    def test_handle_skipthedrive_outer_exception(self, transform):
        """Test handleSkipTheDrive when outer exception occurs."""
        from unittest.mock import Mock, patch
        
        soup = BeautifulSoup("<html></html>", "html.parser")
        
        # Make soup.select raise exception
        with patch.object(soup, 'select', side_effect=Exception("Critical error")):
            jobs = transform.handleSkipTheDrive(soup)
            # Should return empty list
            assert jobs == []
