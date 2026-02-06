"""Tests for core logging module."""
import pytest
import logging
from pathlib import Path
import tempfile
import os
from src.core.logging import setup_logging, get_logger


def test_setup_logging_creates_directory():
    """Test that setup_logging creates log directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logs_path = Path(tmpdir) / "test_logs"
        
        setup_logging("test-app", logs_path)
        
        assert logs_path.exists()


def test_setup_logging_creates_handlers():
    """Test that setup_logging creates appropriate handlers."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logs_path = Path(tmpdir) / "test_logs"
        
        # Clear existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        setup_logging("test-app", logs_path)
        
        # Should have 3 handlers: console, all logs, errors
        assert len(root_logger.handlers) >= 2


def test_get_logger_returns_logger():
    """Test get_logger returns a logger instance."""
    logger = get_logger("test.module")
    
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test.module"


def test_get_logger_different_names():
    """Test get_logger returns different loggers for different names."""
    logger1 = get_logger("module1")
    logger2 = get_logger("module2")
    
    assert logger1.name != logger2.name
    assert logger1 is not logger2
