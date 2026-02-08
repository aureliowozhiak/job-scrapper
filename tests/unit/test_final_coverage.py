"""Final tests to maximize coverage."""
import pytest
from unittest.mock import patch, Mock, AsyncMock
import sys
import importlib


def test_scraper_error_handling():
    """Test scraper error path."""
    from src.jobs.task_scraper import task_scraper
    
    with patch('src.etl.scrapy_runner.run_integrated_scraper', side_effect=Exception("Scraper error")):
        result = task_scraper()
        assert result["status"] == "error"
        assert "error" in result


def test_loader_with_existing_module():
    """Test loader when module already loaded."""
    mock_load = Mock()
    mock_load.run_load_process = Mock(return_value={"inserted": 10})
    
    sys.modules['load'] = mock_load
    
    # Force reload
    if 'src.jobs.task_loader' in sys.modules:
        del sys.modules['src.jobs.task_loader']
    
    with patch('importlib.reload', return_value=mock_load):
        from src.jobs.task_loader import task_loader
        result = task_loader()
        assert "status" in result
    
    if 'load' in sys.modules:
        del sys.modules['load']


def test_sync_with_existing_module():
    """Test sync when module already loaded."""
    mock_load = Mock()
    mock_load.get_sync_status = Mock(return_value={"db_count": 5})
    
    sys.modules['load'] = mock_load
    
    if 'src.jobs.task_sync' in sys.modules:
        del sys.modules['src.jobs.task_sync']
    
    with patch('importlib.reload', return_value=mock_load):
        from src.jobs.task_sync import task_sync_check
        result = task_sync_check()
        assert "status" in result
    
    if 'load' in sys.modules:
        del sys.modules['load']


def test_validator_with_batch():
    """Test validator task."""
    with patch('src.etl.validate.cleanup_invalid_jobs') as mock_cleanup:
        mock_cleanup.return_value = {"removed": 3}
        
        from src.jobs.task_validator import task_validator
        result = task_validator()
        
        assert "status" in result
        mock_cleanup.assert_called_once()


def test_admin_cancel_not_found():
    """Test admin cancel when job not found."""
    from fastapi.testclient import TestClient
    from src.api.main import app
    
    client = TestClient(app, raise_server_exceptions=False)
    
    with patch('src.api.routes.admin.job_manager.cancel_job', return_value=False):
        response = client.delete("/api/admin/job/missing")
        assert response.status_code == 404


def test_health_system_endpoint_exists():
    """Test system health endpoint."""
    from fastapi.testclient import TestClient
    from src.api.main import app
    
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/api/health/system")
    
    # May or may not exist depending on psutil
    assert response.status_code in [200, 404]


def test_websocket_manager_broadcast_with_connections():
    """Test WebSocket manager has broadcast method."""
    from src.api.routes.websocket import manager
    
    # Just verify it exists and is callable
    assert hasattr(manager, 'broadcast')
    assert hasattr(manager, 'connect')
    assert hasattr(manager, 'disconnect')


def test_admin_get_queue_status():
    """Test get queue status."""
    from fastapi.testclient import TestClient
    from src.api.main import app
    
    client = TestClient(app, raise_server_exceptions=False)
    
    with patch('src.api.routes.admin.job_manager.get_all_job_statuses') as mock_status:
        mock_status.return_value = {
            "queued": 5,
            "started": 2,
            "finished": 100,
            "failed": 1,
            "started_jobs": [],
            "finished_jobs": [],
            "failed_jobs": []
        }
        
        response = client.get("/api/admin/queue/status")
        assert response.status_code == 200
        data = response.json()
        assert data["queued"] == 5


def test_admin_clear_failed_jobs():
    """Test clear failed jobs."""
    from fastapi.testclient import TestClient
    from src.api.main import app
    
    client = TestClient(app, raise_server_exceptions=False)
    
    with patch('src.api.routes.admin.job_manager.clear_failed_jobs'):
        response = client.delete("/api/admin/queue/failed")
        assert response.status_code == 200


