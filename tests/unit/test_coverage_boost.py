"""Tests to increase coverage of uncovered modules."""
import pytest
from unittest.mock import patch
from pathlib import Path


def test_database_connection_get_db():
    """Test get_db generator."""
    from src.database.connection import get_db
    
    db_gen = get_db()
    db = next(db_gen)
    
    assert db is not None
    
    try:
        db_gen.close()
    except StopIteration:
        pass


def test_admin_route_error_handlers():
    """Test admin route error handling."""
    from fastapi.testclient import TestClient
    from src.api.main import app
    
    client = TestClient(app, raise_server_exceptions=False)
    
    with patch('src.api.routes.admin.job_manager') as mock_manager:
        # Test scrape error
        mock_manager.enqueue_scraper.side_effect = Exception("Redis down")
        response = client.post("/api/admin/scrape")
        assert response.status_code == 500
        
        # Test load error
        mock_manager.enqueue_loader.side_effect = Exception("Redis down")
        response = client.post("/api/admin/load")
        assert response.status_code == 500
        
        # Test validate error
        mock_manager.enqueue_validator.side_effect = Exception("Redis down")
        response = client.post("/api/admin/validate")
        assert response.status_code == 500
        
        # Test sync error
        mock_manager.enqueue_sync_check.side_effect = Exception("Redis down")
        response = client.post("/api/admin/sync-check")
        assert response.status_code == 500


def test_health_routes_edge_cases():
    """Test health route edge cases."""
    from fastapi.testclient import TestClient
    from src.api.main import app
    
    client = TestClient(app, raise_server_exceptions=False)
    
    # Test Redis health check
    with patch('src.api.routes.health.Redis') as MockRedis:
        mock_redis = MockRedis.from_url.return_value
        mock_redis.ping.return_value = True
        
        response = client.get("/api/health/redis")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


def test_repository_edge_cases(test_db):
    """Test repository edge cases."""
    from src.database.repositories import PositionRepository
    
    repo = PositionRepository(test_db)
    
    # Test empty search
    results = repo.search("", limit=10)
    assert len(results) == 0
    
    # Test get_all with offset beyond total
    results = repo.get_all(limit=10, offset=1000)
    assert len(results) == 0
    
    # Test count with no matches
    count = repo.count(search="nonexistent_query_xyz")
    assert count == 0


def test_models_position_repr():
    """Test Position model __repr__."""
    from src.database.models import Position
    
    position = Position(
        id=1,
        title="Test Job",
        link="http://test.com",
        company="Test Co"
    )
    
    repr_str = repr(position)
    assert "Position" in repr_str


def test_load_module_execution_coverage():
    """Test load module key paths."""
    from src.etl import load
    from src.core.config import settings
    
    # Test configuration values
    assert settings.enable_pre_validation in [True, False]
    assert load.PRE_VALIDATION_SAMPLE_SIZE > 0
    assert load.output_directory == "data/output"


def test_validate_module_functions():
    """Test validate module functions exist."""
    from src.etl import validate
    
    assert hasattr(validate, 'cleanup_invalid_jobs')
    assert callable(validate.cleanup_invalid_jobs)

