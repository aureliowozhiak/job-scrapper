"""Unit tests for logger module."""
import pytest
import logging
from pathlib import Path
from src.core.logging import get_logger, setup_logging


class TestLogger:
    """Test cases for logger module."""
    
    def test_get_logger_basic(self):
        """Test basic logger creation."""
        logger = get_logger("test_module")
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"
    
    def test_setup_logging_creates_handlers(self):
        """Test that setup_logging creates proper handlers."""
        # Clear existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        setup_logging("test_app")
        
        # Should have 3 handlers: console, file, error file
        assert len(root_logger.handlers) == 3
    
    def test_setup_logging_creates_logs_directory(self):
        """Test that setup_logging creates logs directory."""
        import tempfile
        import shutil
        
        # Use a temp directory
        temp_dir = Path(tempfile.mkdtemp())
        try:
            setup_logging("test_app", temp_dir)
            assert temp_dir.exists()
            assert temp_dir.is_dir()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_logger_works(self):
        """Test that logger works without errors."""
        setup_logging("test_app")
        logger = get_logger("test_format")
        
        # Logger should work without errors
        logger.info("Test message")
        logger.debug("Debug message")
        logger.warning("Warning message")
        logger.error("Error message")
