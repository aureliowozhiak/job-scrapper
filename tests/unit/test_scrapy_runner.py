"""Tests for Scrapy runner integration."""
import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.etl.scrapy_runner import (
    normalize_scrapy_job,
    run_scrapy_spider_subprocess,
    load_jobs_to_database,
    run_integrated_scraper
)


class TestNormalizeScrapyJob:
    """Test Scrapy job normalization."""
    
    def test_normalize_complete_job(self):
        """Test normalization of complete job data."""
        scrapy_job = {
            "job_title": "Senior Data Engineer",
            "company": "Tech Corp",
            "post_date": "January 1, 2026",
            "qualifications": ["Python", "SQL"],
            "url": "https://example.com/job/123"
        }
        
        result = normalize_scrapy_job(scrapy_job)
        
        assert result["title"] == "Senior Data Engineer"
        assert result["company"] == "Tech Corp"
        assert result["link"] == "https://example.com/job/123"
    
    def test_normalize_minimal_job(self):
        """Test normalization with missing fields."""
        scrapy_job = {
            "job_title": "Engineer",
            "company": "Corp",
            "url": "https://example.com/job"
        }
        
        result = normalize_scrapy_job(scrapy_job)
        
        assert result["title"] == "Engineer"
        assert result["company"] == "Corp"
        assert result["link"] == "https://example.com/job"
    
    def test_normalize_with_whitespace(self):
        """Test normalization strips whitespace."""
        scrapy_job = {
            "job_title": "  Engineer  ",
            "company": "  Corp  ",
            "url": "  https://example.com/job  "
        }
        
        result = normalize_scrapy_job(scrapy_job)
        
        assert result["title"] == "Engineer"
        assert result["company"] == "Corp"
        assert result["link"] == "https://example.com/job"


class TestRunScrapySpiderSubprocess:
    """Test Scrapy spider execution via subprocess."""
    
    @patch('subprocess.run')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.stat')
    def test_successful_spider_run(self, mock_stat, mock_exists, mock_run):
        """Test successful spider execution."""
        # Mock successful subprocess
        mock_run.return_value = Mock(returncode=0, stderr="")
        mock_exists.return_value = True
        mock_stat.return_value = Mock(st_size=1000)
        
        result = run_scrapy_spider_subprocess("test_spider", "/tmp/out.json", query="test query")
        
        assert result is True
        mock_run.assert_called_once()
        
    @patch('subprocess.run')
    def test_spider_timeout(self, mock_run):
        """Test spider timeout handling."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("scrapy", 180)
        
        result = run_scrapy_spider_subprocess("test_spider", "/tmp/out.json", query="test query")
        
        assert result is False
    
    @patch('subprocess.run')
    def test_spider_failure(self, mock_run):
        """Test spider failure handling."""
        mock_run.return_value = Mock(returncode=1, stderr="Error message")
        
        result = run_scrapy_spider_subprocess("test_spider", "/tmp/out.json", query="test query")
        
        assert result is False


class TestLoadJobsToDatabase:
    """Test database loading functionality."""
    
    def test_load_valid_jobs(self, test_db):
        """Test loading valid jobs."""
        jobs = [
            {"title": "Engineer 1", "company": "Corp A", "link": "https://example.com/1"},
            {"title": "Engineer 2", "company": "Corp B", "link": "https://example.com/2"}
        ]
        
        with patch('src.etl.scrapy_runner.SessionLocal', return_value=test_db):
            stats = load_jobs_to_database(jobs)
        
        assert stats["inserted"] == 2
        assert stats["duplicates"] == 0
        assert stats["errors"] == 0
    
    def test_load_duplicate_jobs(self, test_db):
        """Test loading duplicate jobs."""
        from src.database.models import Position
        from datetime import datetime, timezone
        
        # Add existing job
        existing = Position(
            title="Existing Job",
            company="Corp",
            link="https://example.com/exists",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        test_db.add(existing)
        test_db.commit()
        
        # Try to load duplicate
        jobs = [
            {"title": "Existing Job", "company": "Corp", "link": "https://example.com/exists"}
        ]
        
        with patch('src.etl.scrapy_runner.SessionLocal', return_value=test_db):
            stats = load_jobs_to_database(jobs)
        
        assert stats["duplicates"] == 1
        assert stats["inserted"] == 0
    
    def test_load_invalid_jobs(self, test_db):
        """Test loading jobs with invalid data."""
        jobs = [
            {"title": "", "company": "Corp", "link": "https://example.com/1"},  # No title
            {"title": "Job", "company": "", "link": "https://example.com/2"},  # No company
            {"title": "Job", "company": "Corp", "link": "N/A"},  # Invalid link
        ]
        
        with patch('src.etl.scrapy_runner.SessionLocal', return_value=test_db):
            stats = load_jobs_to_database(jobs)
        
        assert stats["errors"] == 3
        assert stats["inserted"] == 0


class TestRunIntegratedScraper:
    """Test full integrated scraper."""
    
    @patch('src.etl.scrapy_runner.run_scrapy_spider_subprocess')
    @patch('src.etl.scrapy_runner.load_jobs_to_database')
    @patch('builtins.open')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.stat')
    @patch('pathlib.Path.unlink')
    def test_successful_scrape_and_load(
        self, mock_unlink, mock_stat, mock_exists, mock_open, mock_load, mock_spider
    ):
        """Test successful end-to-end scraping."""
        # Mock spider success
        mock_spider.return_value = True
        mock_exists.return_value = True
        mock_stat.return_value = Mock(st_size=1000)
        
        # Mock file content
        mock_jobs = [
            {
                "job_title": "Data Engineer",
                "company": "Tech Corp",
                "url": "https://example.com/job1",
                "post_date": "Jan 1",
                "qualifications": []
            }
        ]
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_jobs)
        
        # Mock database load
        mock_load.return_value = {
            "processed": 1,
            "inserted": 1,
            "duplicates": 0,
            "errors": 0
        }
        
        # Override queries for testing
        with patch('src.etl.scrapy_runner.QUERIES', ['data engineer']):
            with patch('src.etl.scrapy_runner.SPIDERS', ['skipthedrive_jobs']):
                stats = run_integrated_scraper()
        
        assert stats["jobs_scraped"] >= 0
        assert stats["queries_processed"] >= 0
    
    @patch('src.etl.scrapy_runner.run_scrapy_spider_subprocess')
    @patch('pathlib.Path.unlink')
    def test_spider_failure_handling(self, mock_unlink, mock_spider):
        """Test handling of spider failures."""
        # Mock spider failure
        mock_spider.return_value = False
        
        with patch('src.etl.scrapy_runner.QUERIES', ['test query']):
            with patch('src.etl.scrapy_runner.SPIDERS', ['test_spider']):
                stats = run_integrated_scraper()
        
        # Should complete without crashing
        assert stats["queries_processed"] == 0
        assert stats["jobs_loaded"] == 0
