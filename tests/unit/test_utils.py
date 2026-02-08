"""Unit tests for Utils module."""
import pytest
from unittest.mock import patch, mock_open, MagicMock
import os
from src.etl.utils import Utils


class TestUtils:
    """Test cases for Utils class."""
    
    @pytest.fixture
    def utils(self):
        """Create Utils instance for testing."""
        return Utils()
    
    @patch('src.etl.utils.os.path.exists')
    @patch('src.etl.utils.os.mkdir')
    def test_create_dir_new_directory(self, mock_mkdir, mock_exists, utils):
        """Test creating a new directory."""
        mock_exists.return_value = False
        
        utils.createDir("/test/directory")
        
        mock_exists.assert_called_once_with("/test/directory")
        mock_mkdir.assert_called_once_with("/test/directory")
    
    @patch('src.etl.utils.os.path.exists')
    @patch('src.etl.utils.os.mkdir')
    def test_create_dir_existing_directory(self, mock_mkdir, mock_exists, utils):
        """Test behavior when directory already exists."""
        mock_exists.return_value = True
        
        utils.createDir("/existing/directory")
        
        mock_exists.assert_called_once_with("/existing/directory")
        mock_mkdir.assert_not_called()
    
    @patch('src.etl.utils.os.listdir')
    def test_list_dir_success(self, mock_listdir, utils):
        """Test listing directory contents."""
        mock_listdir.return_value = ["file1.txt", "file2.txt", "folder1"]
        
        result = utils.listDir("/test/directory")
        
        assert result == ["file1.txt", "file2.txt", "folder1"]
        mock_listdir.assert_called_once_with("/test/directory")
    
    @patch('src.etl.utils.os.listdir')
    def test_list_dir_empty(self, mock_listdir, utils):
        """Test listing empty directory."""
        mock_listdir.return_value = []
        
        result = utils.listDir("/empty/directory")
        
        assert result == []
    
    @patch('builtins.open', new_callable=mock_open, read_data="test file content")
    def test_load_file_success(self, mock_file, utils):
        """Test loading a file."""
        result = utils.loadFile("/test/file.txt")
        
        assert result == "test file content"
        mock_file.assert_called_once_with("/test/file.txt", "r")
    
    @patch('builtins.open', new_callable=mock_open, read_data="")
    def test_load_file_empty(self, mock_file, utils):
        """Test loading an empty file."""
        result = utils.loadFile("/test/empty.txt")
        
        assert result == ""
    
    @patch('builtins.open', side_effect=FileNotFoundError())
    def test_load_file_not_found(self, mock_file, utils):
        """Test loading a non-existent file."""
        with pytest.raises(FileNotFoundError):
            utils.loadFile("/non/existent/file.txt")
    
    @patch('builtins.open', side_effect=PermissionError())
    def test_load_file_permission_error(self, mock_file, utils):
        """Test loading a file without permissions."""
        with pytest.raises(PermissionError):
            utils.loadFile("/forbidden/file.txt")
    
    @patch('src.etl.utils.os.path.exists')
    @patch('src.etl.utils.os.mkdir', side_effect=OSError("Permission denied"))
    def test_create_dir_permission_error(self, mock_mkdir, mock_exists, utils):
        """Test creating directory with permission error."""
        mock_exists.return_value = False
        
        with pytest.raises(OSError):
            utils.createDir("/forbidden/directory")
    
    @patch('src.etl.utils.os.listdir', side_effect=FileNotFoundError())
    def test_list_dir_not_found(self, mock_listdir, utils):
        """Test listing non-existent directory."""
        with pytest.raises(FileNotFoundError):
            utils.listDir("/non/existent/directory")
