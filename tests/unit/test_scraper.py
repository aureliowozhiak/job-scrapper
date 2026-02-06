"""Unit tests for the scraper orchestrator."""
import pytest
from unittest.mock import patch, MagicMock, mock_open
import json
from datetime import datetime
from src.etl.scraper import run_scraper

class TestScraper:
    """Test cases for scraper.py."""

    @patch('src.etl.scraper.Utils')
    @patch('src.etl.scraper.Extract')
    @patch('src.etl.scraper.Transform')
    @patch('src.etl.scraper.datetime')
    def test_run_scraper_success(self, mock_datetime, mock_transform_cls, mock_extract_cls, mock_utils_cls):
        """Test successful execution of run_scraper."""
        # Setup mocks
        mock_datetime.now.return_value = datetime(2026, 2, 5)
        
        mock_utils = mock_utils_cls.return_value
        mock_extract = mock_extract_cls.return_value
        mock_transform = mock_transform_cls.return_value
        
        # Configure utils behavior
        mock_utils.listDir.side_effect = [
            ["site1"], # for directories = utils.listDir(f"{path}/{year}/{month}/{day}")
            ["file1.html"] # for files = utils.listDir(...) inside the loop
        ]
        mock_utils.loadFile.return_value = "<html><body>Job</body></html>"
        
        # Configure extract behavior
        mock_extract.extractData.return_value = True
        
        # Configure transform behavior
        mock_transform.soupHtml.return_value = MagicMock()
        mock_transform.getJobs.return_value = [{"title": "Job 1"}]
        
        # Mock open for json.dump
        with patch('builtins.open', mock_open()) as m_open:
            stats = run_scraper()
            
            # Assertions
            assert stats["queries_processed"] == 20 # Total in scraper.py
            assert stats["sites_processed"] == 1
            assert stats["total_jobs"] == 1
            assert "2026/2/5" in stats["output_dir"]
            
            # Check if directories were created
            assert mock_utils.createDir.call_count >= 8 # Data lake and output structure
            
            # Check if open was called to save JSON
            m_open.assert_called()

    @patch('src.etl.scraper.Utils')
    @patch('src.etl.scraper.Extract')
    @patch('src.etl.scraper.Transform')
    @patch('src.etl.scraper.datetime')
    def test_run_scraper_partial_failures(self, mock_datetime, mock_transform_cls, mock_extract_cls, mock_utils_cls):
        """Test run_scraper with some failures."""
        mock_datetime.now.return_value = datetime(2026, 2, 5)
        
        mock_utils = mock_utils_cls.return_value
        mock_extract = mock_extract_cls.return_value
        mock_transform = mock_transform_cls.return_value
        
        # Fail some queries
        mock_extract.extractData.side_effect = [True] * 10 + [False] * 10
        
        # Mock directories and files
        mock_utils.listDir.side_effect = [
            ["site1", "site2"],
            ["file1.html"], # site1 files
            ["file2.html"]  # site2 files
        ]
        
        # Fail one file processing
        mock_utils.loadFile.side_effect = [
            "html1",
            Exception("Read error")
        ]
        
        mock_transform.getJobs.return_value = [{"title": "Job"}]
        
        with patch('builtins.open', mock_open()):
            stats = run_scraper()
            
            assert stats["queries_processed"] == 10
            assert stats["sites_processed"] >= 1
            assert stats["total_jobs"] == 1

    @patch('src.etl.scraper.Utils')
    def test_run_scraper_dir_creation_failure(self, mock_utils_cls):
        """Test run_scraper failing to create directories."""
        mock_utils = mock_utils_cls.return_value
        mock_utils.createDir.side_effect = Exception("OS Error")
        
        with pytest.raises(Exception, match="OS Error"):
            run_scraper()

    @patch('src.etl.scraper.Utils')
    @patch('src.etl.scraper.Extract')
    @patch('src.etl.scraper.Transform')
    def test_run_scraper_save_failure(self, mock_transform_cls, mock_extract_cls, mock_utils_cls):
        """Test run_scraper failing to save JSON (IOError)."""
        mock_utils = mock_utils_cls.return_value
        mock_utils.listDir.side_effect = [["site1"], ["file1.html"]]
        mock_utils.loadFile.return_value = "html"
        
        with patch('builtins.open', side_effect=IOError("Write failed")):
            stats = run_scraper()
            assert stats["sites_processed"] == 0 # Saved failed
            assert stats["total_jobs"] == 0

    @patch('src.etl.scraper.run_scraper')
    def test_main_block(self, mock_run):
        """Test the main() function."""
        from src.etl.scraper import main
        mock_run.return_value = {
            "queries_processed": 1,
            "queries_total": 20,
            "sites_processed": 1,
            "total_jobs": 5,
            "output_dir": "dir"
        }
        
        with patch('builtins.print'):
            main()
            assert mock_run.called

    @patch('src.etl.scraper.Utils')
    @patch('src.etl.scraper.Extract')
    @patch('src.etl.scraper.Transform')
    @patch('src.etl.scraper.datetime')
    def test_run_scraper_loop_exceptions(self, mock_datetime, mock_transform_cls, mock_extract_cls, mock_utils_cls):
        """Test scraper with exceptions in loops (lines 99-100, 153-154)."""
        mock_datetime.now.return_value = datetime(2026, 2, 5)
        mock_utils = mock_utils_cls.return_value
        mock_extract = mock_extract_cls.return_value
        
        # 1. Exception in query loop (line 99-100)
        # Force exception for the first query, success for others
        mock_extract.extractData.side_effect = [Exception("Extract break")] + [True] * 19
        
        # 2. Exception in site loop (line 153-154)
        mock_utils.listDir.side_effect = [
            ["site_ok", "site_fail"], # root directories
            ["file.html"],            # site_ok files
            Exception("Dir list fail") # site_fail - triggers line 153
        ]
        
        mock_utils.loadFile.return_value = "html"
        mock_transform_cls.return_value.getJobs.return_value = [{"title": "J"}]
        
        with patch('builtins.open', mock_open()):
            stats = run_scraper()
            
            # site_ok should have finished, site_fail failed
            assert stats["queries_processed"] == 19
            assert stats["sites_processed"] == 1
            assert stats["total_jobs"] == 1

