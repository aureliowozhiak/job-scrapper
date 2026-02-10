"""Integration test for task enrichment in task manager."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone


def test_task_manager_enrichment_flow(authenticated_client):
    """Test that task status endpoint returns enriched metrics."""
    
    # Mock a job with enriched metrics
    mock_job = MagicMock()
    mock_job.id = "pipeline-scraper-20260208000000"
    mock_job.get_status.return_value = "finished"
    mock_job.started_at = datetime.now(timezone.utc)
    mock_job.ended_at = datetime.now(timezone.utc)
    mock_job.is_failed = False
    mock_job.exc_info = None
    mock_job.result = {
        "status": "completed",
        "stats": {
            "queries_processed": 5,
            "jobs_scraped": 100,
            "jobs_loaded": 95,
            "duplicates": 5,
            "errors": 0,
            "spiders": {"skipthedrive": 100}
        }
    }
    
    with patch('src.jobs.manager.Job.fetch', return_value=mock_job):
        # Test the admin endpoint
        response = authenticated_client.get("/api/admin/job/pipeline-scraper-20260208000000")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify basic fields
        assert data["id"] == "pipeline-scraper-20260208000000"
        assert data["status"] == "finished"
        
        # Verify enriched metrics
        assert "job_type" in data
        assert data["job_type"] == "scraper"
        assert "jobs_processed" in data
        assert data["jobs_processed"] == 100
        assert "success_rate" in data
        assert data["success_rate"] == 95.0
        assert "detailed_stats" in data
        assert data["detailed_stats"]["queries_processed"] == 5
        assert data["detailed_stats"]["jobs_scraped"] == 100


def test_loader_enrichment(authenticated_client):
    """Test loader task enrichment."""
    
    mock_job = MagicMock()
    mock_job.id = "pipeline-loader-20260208000000"
    mock_job.get_status.return_value = "finished"
    mock_job.started_at = datetime.now(timezone.utc)
    mock_job.ended_at = datetime.now(timezone.utc)
    mock_job.is_failed = False
    mock_job.exc_info = None
    mock_job.result = {
        "status": "completed",
        "stats": {
            "processed": 95,
            "inserted": 90,
            "duplicates": 5,
            "errors": 0,
            "pre_rejected": 0
        }
    }
    
    with patch('src.jobs.manager.Job.fetch', return_value=mock_job):
        response = authenticated_client.get("/api/admin/job/pipeline-loader-20260208000000")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["job_type"] == "loader"
        assert data["jobs_processed"] == 95
        assert data["success_rate"] == 94.74
        assert data["detailed_stats"]["inserted"] == 90


def test_validator_enrichment(authenticated_client):
    """Test validator task enrichment."""
    
    mock_job = MagicMock()
    mock_job.id = "pipeline-validator-20260208000000"
    mock_job.get_status.return_value = "finished"
    mock_job.started_at = datetime.now(timezone.utc)
    mock_job.ended_at = datetime.now(timezone.utc)
    mock_job.is_failed = False
    mock_job.exc_info = None
    mock_job.result = {
        "status": "completed",
        "stats": {
            "total_checked": 90,
            "valid": 85,
            "removed": 5,
            "errors": []
        }
    }
    
    with patch('src.jobs.manager.Job.fetch', return_value=mock_job):
        response = authenticated_client.get("/api/admin/job/pipeline-validator-20260208000000")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["job_type"] == "validator"
        assert data["jobs_processed"] == 90
        assert data["success_rate"] == 94.44
        assert data["detailed_stats"]["valid"] == 85
