"""Unit tests for RQ task modules."""
import pytest
from unittest.mock import patch, MagicMock
import sys

class TestTaskModules:
    """Test RQ task wrapper functions."""
    
    def test_task_scraper_callable(self):
        """Test scraper task is callable."""
        from src.jobs.task_scraper import task_scraper
        assert callable(task_scraper)
    
    def test_task_loader_callable(self):
        """Test loader task is callable."""
        from src.jobs.task_loader import task_loader
        assert callable(task_loader)
    
    def test_task_validator_callable(self):
        """Test validator task is callable."""
        from src.jobs.task_validator import task_validator
        assert callable(task_validator)
    
    def test_task_sync_callable(self):
        """Test sync task is callable."""
        from src.jobs.task_sync import task_sync_check
        assert callable(task_sync_check)
    
    @patch('src.etl.scrapy_runner.run_integrated_scraper')
    def test_task_scraper_execution(self, mock_scraper):
        """Test scraper task executes scraper module."""
        from src.jobs.task_scraper import task_scraper
        
        mock_scraper.return_value = {
            "queries_processed": 20,
            "queries_total": 20,
            "sites_processed": 2,
            "total_jobs": 150
        }
        
        result = task_scraper()
        
        assert result["status"] == "completed"
        assert "message" in result
        assert "stats" in result
        mock_scraper.assert_called_once()

    @patch('src.etl.load.run_load_process')
    def test_task_loader_execution(self, mock_load):
        """Test loader task execution."""
        from src.jobs.task_loader import task_loader
        
        mock_load.return_value = {"inserted": 10}
        
        result = task_loader()
        
        assert result["status"] == "completed"
        assert result["stats"]["inserted"] == 10
        mock_load.assert_called_once()

    @patch('src.etl.validate.cleanup_invalid_jobs')
    def test_task_validator_execution(self, mock_validate):
        """Test validator task execution."""
        from src.jobs.task_validator import task_validator
        
        mock_validate.return_value = {"removed": 5}
        
        result = task_validator()
        
        assert result["status"] == "completed"
        assert result["stats"]["removed"] == 5
        mock_validate.assert_called_once()

    @patch('src.etl.load.get_sync_status')
    def test_task_sync_execution(self, mock_sync):
        """Test sync task execution."""
        from src.jobs.task_sync import task_sync_check
        
        mock_sync.return_value = {"local": 100, "db": 100}
        
        result = task_sync_check()
        
        assert result["status"] == "completed"
        assert result["data"]["local"] == 100
        mock_sync.assert_called_once()
