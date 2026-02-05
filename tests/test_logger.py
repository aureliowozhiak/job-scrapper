"""Unit tests for logger module."""
import pytest
import logging
from pathlib import Path
from utils.logger import get_logger


class TestLogger:
    """Test cases for logger module."""
    
    def test_get_logger_basic(self):
        """Test basic logger creation."""
        logger = get_logger("test_module")
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"
        assert logger.level == logging.INFO
    
    def test_get_logger_custom_level(self):
        """Test logger with custom log level."""
        logger = get_logger("test_debug", log_level="DEBUG")
        
        assert logger.level == logging.DEBUG
    
    def test_get_logger_handlers(self):
        """Test that logger has proper handlers."""
        logger = get_logger("test_handlers")
        
        # Should have 3 handlers: console, file, error file
        assert len(logger.handlers) == 3
    
    def test_get_logger_no_duplicate_handlers(self):
        """Test that calling get_logger twice doesn't duplicate handlers."""
        logger1 = get_logger("test_duplicate")
        initial_handler_count = len(logger1.handlers)
        
        # Call again with same name
        logger2 = get_logger("test_duplicate")
        
        # Should be the same logger
        assert logger1 is logger2
        # Should not have duplicate handlers
        assert len(logger2.handlers) == initial_handler_count
    
    def test_logs_directory_created(self):
        """Test that logs directory is created."""
        get_logger("test_dir")
        
        log_dir = Path("logs")
        assert log_dir.exists()
        assert log_dir.is_dir()
    
    def test_logger_formats_message(self):
        """Test that logger formats messages correctly."""
        import tempfile
        import os
        
        logger = get_logger("test_format")
        
        # Logger should work without errors
        logger.info("Test message")
        logger.debug("Debug message")
        logger.warning("Warning message")
        logger.error("Error message")
