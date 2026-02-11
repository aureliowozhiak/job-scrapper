"""Tests for admin routes."""
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from src.api.main import app
from src.core.permissions import require_admin


@pytest.fixture
def authenticated_client():
    """Return a test client with admin authentication mocked."""
    async def mock_require_admin():
        return True
    
    app.dependency_overrides[require_admin] = mock_require_admin
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@patch('src.api.routes.admin.job_manager')
def test_trigger_scrape(mock_manager, authenticated_client):
    """Test triggering scrape job."""
    mock_manager.enqueue_scraper.return_value = "scraper-123"
    
    response = authenticated_client.post("/api/admin/scrape")
    
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "scraper-123"
    assert data["status"] == "queued"
    mock_manager.enqueue_scraper.assert_called_once()


@patch('src.api.routes.admin.job_manager')
def test_trigger_load(mock_manager, authenticated_client):
    """Test triggering load job."""
    mock_manager.enqueue_loader.return_value = "loader-123"
    
    response = authenticated_client.post("/api/admin/load")
    
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "loader-123"


@patch('src.api.routes.admin.job_manager')
def test_trigger_validate(mock_manager, authenticated_client):
    """Test triggering validate job."""
    mock_manager.enqueue_validator.return_value = "validator-123"
    
    response = authenticated_client.post("/api/admin/validate")
    
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "validator-123"


@patch('src.api.routes.admin.job_manager')
def test_trigger_sync_check(mock_manager, authenticated_client):
    """Test triggering sync check job."""
    mock_manager.enqueue_sync_check.return_value = "sync-123"
    
    response = authenticated_client.post("/api/admin/sync-check")
    
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "sync-123"


@patch('src.api.routes.admin.job_manager')
def test_trigger_pipeline(mock_manager, authenticated_client):
    """Test triggering full pipeline."""
    mock_manager.enqueue_pipeline.return_value = ["scraper-123", "validator-123", "loader-123", "cleanup-123"]
    
    response = authenticated_client.post("/api/admin/pipeline")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["job_ids"]) == 4
    assert data["steps"] == ["scraper", "validator", "loader", "cleanup"]


@patch('src.api.routes.admin.job_manager')
def test_get_job_status(mock_manager, authenticated_client):
    """Test getting job status."""
    mock_manager.get_job_status.return_value = {
        "id": "test-123",
        "status": "finished",
        "result": {"message": "Done"}
    }
    
    response = authenticated_client.get("/api/admin/job/test-123")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test-123"
    assert data["status"] == "finished"


@patch('src.api.routes.admin.job_manager')
def test_get_queue_status(mock_manager, authenticated_client):
    """Test getting queue status."""
    mock_manager.get_all_job_statuses.return_value = {
        "queued": 2,
        "started": 1,
        "finished": 10,
        "failed": 0,
        "started_jobs": ["job-1"],
        "finished_jobs": ["job-2", "job-3"],
        "failed_jobs": []
    }
    
    response = authenticated_client.get("/api/admin/queue/status")
    
    assert response.status_code == 200
    data = response.json()
    assert data["queued"] == 2
    assert data["started"] == 1


@patch('src.api.routes.admin.job_manager')
def test_cancel_job(mock_manager, authenticated_client):
    """Test cancelling a job."""
    mock_manager.cancel_job.return_value = True
    
    response = authenticated_client.delete("/api/admin/job/test-123")
    
    assert response.status_code == 200
    data = response.json()
    assert "cancelled" in data["message"]


@patch('src.api.routes.admin.job_manager')
def test_cancel_job_not_found(mock_manager, authenticated_client):
    """Test cancelling non-existent job."""
    mock_manager.cancel_job.return_value = False
    
    response = authenticated_client.delete("/api/admin/job/nonexistent")
    
    assert response.status_code == 404


@patch('src.api.routes.admin.job_manager')
def test_clear_failed_jobs(mock_manager, authenticated_client):
    """Test clearing failed jobs."""
    mock_manager.clear_failed_jobs.return_value = None
    
    response = authenticated_client.delete("/api/admin/queue/failed")
    
    assert response.status_code == 200
    data = response.json()
    assert "cleared" in data["message"]


@patch('src.api.routes.admin.job_manager')
def test_enqueue_error_handling(mock_manager, authenticated_client):
    """Test error handling when enqueue fails."""
    mock_manager.enqueue_scraper.side_effect = Exception("Redis connection failed")
    
    response = authenticated_client.post("/api/admin/scrape")
    
    assert response.status_code == 500
    data = response.json()
    assert "error" in data["detail"] or "Failed" in data["detail"]
