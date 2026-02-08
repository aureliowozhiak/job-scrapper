"""Unit tests for Validate module."""
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from src.etl.validate import (
    validate_link,
    cleanup_invalid_jobs,
    validate_json_jobs
)


class TestValidateModule:
    """Test cases for validate.py module."""
    
    @patch('src.etl.validate.requests.head')
    @patch('src.etl.validate.time.sleep')  # Mock sleep to speed up tests
    def test_validate_link_success(self, mock_sleep, mock_head):
        """Test validation of a valid link."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response
        
        is_valid, status_code = validate_link("https://example.com/job/1")
        
        assert is_valid is True
        assert status_code == 200
        mock_head.assert_called_once()
    
    @patch('src.etl.validate.requests.head')
    @patch('src.etl.validate.time.sleep')
    def test_validate_link_404(self, mock_sleep, mock_head):
        """Test validation of a 404 link."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_head.return_value = mock_response
        
        is_valid, status_code = validate_link("https://example.com/job/404")
        
        assert is_valid is False
        assert status_code == 404
    
    @patch('src.etl.validate.requests.head')
    @patch('src.etl.validate.time.sleep')
    def test_validate_link_redirect(self, mock_sleep, mock_head):
        """Test validation of redirect (within 2xx after redirect)."""
        mock_response = Mock()
        mock_response.status_code = 200  # After following redirects
        mock_head.return_value = mock_response
        
        is_valid, status_code = validate_link("https://example.com/job/redirect")
        
        assert is_valid is True
    
    @patch('src.etl.validate.requests.head')
    @patch('src.etl.validate.time.sleep')
    def test_validate_link_timeout(self, mock_sleep, mock_head):
        """Test handling of timeout."""
        mock_head.side_effect = requests.Timeout()
        
        is_valid, status_code = validate_link("https://example.com/job/timeout")
        
        assert is_valid is False
        assert status_code == 408  # Request Timeout
    
    @patch('src.etl.validate.requests.head')
    @patch('src.etl.validate.time.sleep')
    def test_validate_link_connection_error(self, mock_sleep, mock_head):
        """Test handling of connection error."""
        mock_head.side_effect = requests.ConnectionError()
        
        is_valid, status_code = validate_link("https://example.com/job/error")
        
        assert is_valid is False
        assert status_code == 0
    
    @patch('src.etl.validate.requests.head')
    @patch('src.etl.validate.time.sleep')
    def test_validate_link_generic_exception(self, mock_sleep, mock_head):
        """Test handling of generic exception."""
        mock_head.side_effect = Exception("Unexpected error")
        
        is_valid, status_code = validate_link("https://example.com/job/error")
        
        assert is_valid is False
        assert status_code == 500
    
    @patch('src.etl.validate.sqlite3.connect')
    @patch('src.etl.validate.validate_link')
    def test_cleanup_invalid_jobs_all_valid(self, mock_validate, mock_connect):
        """Test cleanup with all valid links."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock job data
        job_row = {
            "id": 1,
            "title": "Python Developer",
            "link": "https://example.com/job/1",
            "company": "TechCorp",
            "created_at": "2026-01-01"
        }
        mock_cursor.fetchall.return_value = [job_row]
        
        # All links are valid
        mock_validate.return_value = (True, 200)
        
        result = cleanup_invalid_jobs()
        
        assert result["total_checked"] == 1
        assert result["valid"] == 1
        assert result["removed"] == 0
    
    @patch('src.etl.validate.sqlite3.connect')
    @patch('src.etl.validate.validate_link')
    def test_cleanup_invalid_jobs_some_invalid(self, mock_validate, mock_connect):
        """Test cleanup with some invalid links."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock job data
        jobs = [
            {"id": 1, "title": "Job 1", "link": "http://valid.com", "company": "Co1", "created_at": "2026-01-01"},
            {"id": 2, "title": "Job 2", "link": "http://invalid.com", "company": "Co2", "created_at": "2026-01-01"}
        ]
        mock_cursor.fetchall.return_value = jobs
        
        # First valid, second invalid
        mock_validate.side_effect = [(True, 200), (False, 404)]
        
        result = cleanup_invalid_jobs()
        
        assert result["total_checked"] == 2
        assert result["valid"] == 1
        assert result["removed"] == 1
        assert len(result["errors"]) == 1
    
    @patch('src.etl.validate.sqlite3.connect')
    def test_cleanup_invalid_jobs_no_data(self, mock_connect):
        """Test cleanup with no jobs in database."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        
        result = cleanup_invalid_jobs()
        
        assert result["total_checked"] == 0
        assert result["valid"] == 0
        assert result["removed"] == 0
    
    @patch('src.etl.validate.validate_link')
    def test_validate_json_jobs_all_valid(self, mock_validate):
        """Test JSON validation with all valid jobs."""
        jobs = [
            {"title": "Job 1", "link": "http://valid1.com", "company": "Co1"},
            {"title": "Job 2", "link": "http://valid2.com", "company": "Co2"}
        ]
        
        mock_validate.return_value = (True, 200)
        
        valid_jobs, stats = validate_json_jobs(jobs)
        
        assert len(valid_jobs) == 2
        assert stats["total"] == 2
        assert stats["valid"] == 2
        assert stats["rejected"] == 0
    
    @patch('src.etl.validate.validate_link')
    def test_validate_json_jobs_some_invalid(self, mock_validate):
        """Test JSON validation with some invalid jobs."""
        jobs = [
            {"title": "Job 1", "link": "http://valid.com", "company": "Co1"},
            {"title": "Job 2", "link": "http://invalid.com", "company": "Co2"}
        ]
        
        mock_validate.side_effect = [(True, 200), (False, 404)]
        
        valid_jobs, stats = validate_json_jobs(jobs)
        
        assert len(valid_jobs) == 1
        assert stats["total"] == 2
        assert stats["valid"] == 1
        assert stats["rejected"] == 1
    
    @patch('src.etl.validate.validate_link')
    def test_validate_json_jobs_missing_link(self, mock_validate):
        """Test JSON validation with missing link."""
        jobs = [
            {"title": "Job 1", "link": "", "company": "Co1"},
            {"title": "Job 2", "link": "N/A", "company": "Co2"},
            {"title": "Job 3", "link": "http://valid.com", "company": "Co3"}
        ]
        
        mock_validate.return_value = (True, 200)
        
        valid_jobs, stats = validate_json_jobs(jobs)
        
        assert len(valid_jobs) == 1
        assert stats["rejected"] == 2
        # Check rejection reasons
        assert stats["rejected_details"][0]["reason"] == "missing_link"
        assert stats["rejected_details"][1]["reason"] == "missing_link"
    
    @patch('src.etl.validate.validate_link')
    def test_validate_json_jobs_max_limit(self, mock_validate):
        """Test JSON validation with max jobs limit."""
        jobs = [
            {"title": f"Job {i}", "link": f"http://job{i}.com", "company": "Co"}
            for i in range(10)
        ]
        
        mock_validate.return_value = (True, 200)
        
        valid_jobs, stats = validate_json_jobs(jobs, max_jobs=5)
        
        assert stats["total"] == 5  # Only processes first 5
        assert len(valid_jobs) <= 5
    
    @patch('src.etl.validate.requests.head')
    @patch('src.etl.validate.time.sleep')
    def test_validate_link_500_error(self, mock_sleep, mock_head):
        """Test validation of server error (5xx)."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_head.return_value = mock_response
        
        is_valid, status_code = validate_link("https://example.com/job/error")
        
        assert is_valid is False
        assert status_code == 500

    @patch('src.etl.validate.cleanup_invalid_jobs')
    def test_standalone_execution(self, mock_cleanup):
        """Test standalone execution of the script."""
        from src.etl.validate import main
        
        mock_cleanup.return_value = {
            'total_checked': 10,
            'valid': 9,
            'removed': 1,
            'errors': [{'title': 'T', 'company': 'C', 'status_code': 404}]
        }
        
        with patch('builtins.print'):
             # Call the main function
             main()
             
        assert mock_cleanup.called

    def test_run_as_main(self):
        """Test running the module as __main__."""
        with patch('src.etl.validate.cleanup_invalid_jobs') as mock_cleanup:
            mock_cleanup.return_value = {
                'total_checked': 10,
                'valid': 8,
                'removed': 2,
                'errors': [
                    {'title': 'Job1', 'company': 'Co1', 'status_code': 404}
                ]
            }
            
            with patch('builtins.print'):
                from src.etl.validate import main
                main()
                
            assert mock_cleanup.called
