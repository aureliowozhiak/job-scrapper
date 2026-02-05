"""Unit tests for Extract module."""
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from methods.extract import Extract


class TestExtract:
    """Test cases for Extract class."""
    
    @pytest.fixture
    def mock_utils(self):
        """Create a mock Utils object."""
        utils = Mock()
        utils.createDir = Mock()
        return utils
    
    @pytest.fixture
    def extract(self, mock_utils):
        """Create Extract instance for testing."""
        urls = {
            "testsite": {
                "url_q": "https://test.com/search?q=",
                "active": 1
            },
            "inactive": {
                "url_q": "https://inactive.com/search?q=",
                "active": 0
            }
        }
        date = {"year": 2024, "month": 1, "day": 15}
        return Extract(urls, date, mock_utils, path="test_lake")
    
    def test_extract_initialization(self, extract, mock_utils):
        """Test Extract initialization."""
        assert extract.path == "test_lake"
        assert extract.year == 2024
        assert extract.month == 1
        assert extract.day == 15
        assert extract.utils == mock_utils
        assert extract.max_retries == 3
    
    @patch('methods.extract.requests.get')
    def test_successful_request(self, mock_get, extract):
        """Test successful HTTP request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html>Job listings</html>"
        mock_get.return_value = mock_response
        
        response = extract._make_request_with_retry("https://test.com")
        
        assert response.status_code == 200
        assert response.text == "<html>Job listings</html>"
        mock_get.assert_called_once()
    
    @patch('methods.extract.requests.get')
    @patch('methods.extract.time.sleep')
    def test_request_with_retry(self, mock_sleep, mock_get, extract):
        """Test retry logic on connection error."""
        mock_get.side_effect = [
            requests.ConnectionError(),
            requests.ConnectionError(),
            Mock(status_code=200, text="<html>Success</html>")
        ]
        
        response = extract._make_request_with_retry("https://test.com")
        
        assert response.status_code == 200
        assert mock_get.call_count == 3
        assert mock_sleep.call_count == 2
    
    @patch('methods.extract.requests.get')
    def test_request_max_retries_exceeded(self, mock_get, extract):
        """Test that exception is raised after max retries."""
        mock_get.side_effect = requests.ConnectionError()
        
        with pytest.raises(requests.RequestException):
            extract._make_request_with_retry("https://test.com")
        
        assert mock_get.call_count == 3
    
    @patch('methods.extract.requests.get')
    @patch('builtins.open', create=True)
    def test_extract_data_success(self, mock_open, mock_get, extract, mock_utils):
        """Test successful data extraction."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html>Job listings</html>"
        mock_get.return_value = mock_response
        
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        result = extract.extractData("python developer")
        
        assert result is True
        mock_utils.createDir.assert_called()
        mock_file.write.assert_called_with("<html>Job listings</html>")
    
    @patch('methods.extract.requests.get')
    def test_extract_data_skips_inactive_sites(self, mock_get, extract):
        """Test that inactive sites are skipped."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # Should only call for active site
        extract.extractData("test")
        
        # Check that only the active site was queried
        assert mock_get.call_count == 1
    
    @patch('methods.extract.requests.get')
    def test_extract_data_handles_request_error(self, mock_get, extract, mock_utils):
        """Test graceful handling of request errors."""
        mock_get.side_effect = requests.RequestException("Network error")
        
        result = extract.extractData("test")
        
        # Should return False as no sites were successful
        assert result is False
    
    @patch('methods.extract.requests.get')
    @patch('methods.extract.time.sleep')
    def test_request_timeout_retry(self, mock_sleep, mock_get, extract):
        """Test retry on timeout error."""
        mock_get.side_effect = [
            requests.Timeout(),
            Mock(status_code=200, text="<html>Success</html>")
        ]
        
        response = extract._make_request_with_retry("https://test.com")
        
        assert response.status_code == 200
        assert mock_get.call_count == 2
    
    @patch('methods.extract.requests.get')
    def test_request_http_error(self, mock_get, extract):
        """Test HTTP error handling."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError(response=mock_response)
        mock_get.return_value = mock_response
        
        with pytest.raises(requests.HTTPError):
            extract._make_request_with_retry("https://test.com")
    
    @patch('methods.extract.requests.get')
    @patch('methods.extract.time.sleep')
    def test_request_unexpected_error(self, mock_sleep, mock_get, extract):
        """Test handling of unexpected errors."""
        mock_get.side_effect = [
            ValueError("Unexpected error"),
            Mock(status_code=200, text="<html>Success</html>")
        ]
        
        response = extract._make_request_with_retry("https://test.com")
        
        assert response.status_code == 200
        assert mock_get.call_count == 2
    
    @patch('methods.extract.requests.get')
    def test_extract_data_unexpected_status_code(self, mock_get, extract, mock_utils):
        """Test handling of unexpected status codes."""
        mock_response = Mock()
        mock_response.status_code = 204  # No content
        mock_get.return_value = mock_response
        
        result = extract.extractData("test")
        
        # Should return False as status code is not 200
        assert result is False
    
    @patch('methods.extract.requests.get')
    @patch('builtins.open', create=True)
    def test_extract_data_io_error(self, mock_open, mock_get, extract, mock_utils):
        """Test handling of IO errors when writing files."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html>Job listings</html>"
        mock_get.return_value = mock_response
        
        # Simulate IOError when opening file
        mock_open.side_effect = IOError("Disk full")
        
        result = extract.extractData("test")
        
        # Should return False as writing failed
        assert result is False
    
    @patch('methods.extract.requests.get')
    def test_extract_data_generic_exception(self, mock_get, extract, mock_utils):
        """Test handling of generic exceptions during extraction."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # Make createDir raise an exception
        mock_utils.createDir.side_effect = Exception("Unexpected error")
        
        result = extract.extractData("test")
        
        # Should return False as extraction failed
        assert result is False
