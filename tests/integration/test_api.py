"""Integration tests for API endpoints."""
import pytest
from fastapi.testclient import TestClient


def test_health_check(client):
    """Test basic health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "app" in data
    assert "version" in data


def test_health_db_check(client):
    """Test database health check."""
    response = client.get("/api/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_get_jobs_stats_empty(client):
    """Test getting stats for empty database."""
    response = client.get("/api/jobs/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_jobs"] == 0
    assert data["total_companies"] == 0


def test_list_jobs_empty(client):
    """Test listing jobs when database is empty."""
    response = client.get("/api/jobs/")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["count"] == 0
    assert len(data["jobs"]) == 0


def test_create_and_list_jobs(client, test_db, sample_position_data):
    """Test creating and listing jobs."""
    from src.database.repositories import PositionRepository
    
    # Create a job
    repo = PositionRepository(test_db)
    repo.create(**sample_position_data)
    
    # List jobs
    response = client.get("/api/jobs/")
    assert response.status_code == 200
    data = response.json()
    
    assert data["total"] == 1
    assert data["count"] == 1
    assert len(data["jobs"]) == 1
    assert data["jobs"][0]["title"] == sample_position_data["title"]


def test_search_jobs(client, test_db, multiple_positions):
    """Test job search functionality."""
    from src.database.repositories import PositionRepository
    
    repo = PositionRepository(test_db)
    for pos_data in multiple_positions:
        repo.create(**pos_data)
    
    # Search for Python
    response = client.get("/api/jobs/search?q=Python")
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) == 1
    assert "Python" in data[0]["title"]


def test_get_job_by_id(client, test_db, sample_position_data):
    """Test getting a specific job by ID."""
    from src.database.repositories import PositionRepository
    
    repo = PositionRepository(test_db)
    position = repo.create(**sample_position_data)
    
    response = client.get(f"/api/jobs/{position.id}")
    assert response.status_code == 200
    data = response.json()
    
    assert data["id"] == position.id
    assert data["title"] == sample_position_data["title"]


def test_get_nonexistent_job(client):
    """Test getting a job that doesn't exist."""
    response = client.get("/api/jobs/999")
    assert response.status_code == 404


def test_jobs_pagination(client, test_db, multiple_positions):
    """Test job listing pagination."""
    from src.database.repositories import PositionRepository
    
    repo = PositionRepository(test_db)
    for pos_data in multiple_positions:
        repo.create(**pos_data)
    
    # Get first page
    response = client.get("/api/jobs/?limit=2&offset=0")
    assert response.status_code == 200
    data = response.json()
    
    assert data["count"] == 2
    assert data["total"] == 3
    assert data["limit"] == 2
    assert data["offset"] == 0
    
    # Get second page
    response = client.get("/api/jobs/?limit=2&offset=2")
    assert response.status_code == 200
    data = response.json()
    
    assert data["count"] == 1
    assert data["offset"] == 2


def test_jobs_company_filter(client, test_db, multiple_positions):
    """Test filtering jobs by company."""
    from src.database.repositories import PositionRepository
    
    repo = PositionRepository(test_db)
    for pos_data in multiple_positions:
        repo.create(**pos_data)
    
    response = client.get("/api/jobs/?company=Company%20A")
    assert response.status_code == 200
    data = response.json()
    
    assert data["count"] == 1
    assert data["jobs"][0]["company"] == "Company A"


def test_root_renders_html(client):
    """Test that root endpoint renders HTML."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_browse_redirects(client):
    """Test that /browse returns the browse page."""
    response = client.get("/browse", follow_redirects=False)
    assert response.status_code == 200
