"""Comprehensive tests for main.py root endpoint POST actions."""
import pytest
from unittest.mock import patch, MagicMock


def test_root_post_update_action(client):
    """Test POST /with action=update triggers pipeline."""
    with patch('src.jobs.manager.job_manager') as mock_manager:
        mock_manager.enqueue_pipeline.return_value = {"jobs": ["j1", "j2", "j3"]}
        
        response = client.post("/", data={"action": "update"}, follow_redirects=False)
        
        assert response.status_code == 303
        assert "msg=Pipeline" in response.headers["location"]
        mock_manager.enqueue_pipeline.assert_called_once()


def test_root_post_scrape_action(client):
    """Test POST / with action=scrape."""
    with patch('src.jobs.manager.job_manager') as mock_manager:
        mock_manager.enqueue_scraper.return_value = "scraper-123"
        
        response = client.post("/", data={"action": "scrape"}, follow_redirects=False)
        
        assert response.status_code == 303
        assert "msg=Scraping" in response.headers["location"]
        mock_manager.enqueue_scraper.assert_called_once()


def test_root_post_load_action(client):
    """Test POST / with action=load."""
    with patch('src.jobs.manager.job_manager') as mock_manager:
        mock_manager.enqueue_loader.return_value = "loader-123"
        
        response = client.post("/", data={"action": "load"}, follow_redirects=False)
        
        assert response.status_code == 303
        assert "msg=Loading" in response.headers["location"]
        mock_manager.enqueue_loader.assert_called_once()


def test_root_post_validate_action(client):
    """Test POST / with action=validate."""
    with patch('src.jobs.manager.job_manager') as mock_manager:
        mock_manager.enqueue_validator.return_value = "validator-123"
        
        response = client.post("/", data={"action": "validate"}, follow_redirects=False)
        
        assert response.status_code == 303
        assert "msg=Valida" in response.headers["location"]
        mock_manager.enqueue_validator.assert_called_once()


def test_root_post_sync_action(client):
    """Test POST / with action=sync."""
    with patch('src.jobs.manager.job_manager') as mock_manager:
        mock_manager.enqueue_sync_check.return_value = "sync-123"
        
        response = client.post("/", data={"action": "sync"}, follow_redirects=False)
        
        assert response.status_code == 303
        assert "msg=Sync" in response.headers["location"]
        mock_manager.enqueue_sync_check.assert_called_once()


def test_root_post_search_action_with_word(client, test_db):
    """Test POST / with action=search and word parameter."""
    from src.database.models import Position
    
    # Add test data
    test_db.add(Position(title="Python Developer", link="http://test.com", company="TestCo"))
    test_db.commit()
    
    response = client.post(
        "/",
        data={"action": "search", "word": "Python"},
        follow_redirects=False
    )
    
    # Should return the page with results (200) or redirect
    assert response.status_code in [200, 303]


def test_root_post_search_action_without_word(client):
    """Test POST / with action=search but no word."""
    response = client.post(
        "/",
        data={"action": "search"},
        follow_redirects=False
    )
    
    assert response.status_code == 303
    assert "error=Digite" in response.headers["location"]


def test_root_post_pipeline_action(client):
    """Test POST / with action=pipeline."""
    with patch('src.jobs.manager.job_manager') as mock_manager:
        mock_manager.enqueue_pipeline.return_value = {"jobs": ["j1"]}
        
        response = client.post("/", data={"action": "pipeline"}, follow_redirects=False)
        
        # Should redirect or return 200
        assert response.status_code in [200, 303]


def test_root_post_unknown_action(client):
    """Test POST / with unknown action."""
    response = client.post(
        "/",
        data={"action": "unknown_action"},
        follow_redirects=False
    )
    
    # Should redirect back to homepage
    assert response.status_code in [200, 303, 307]


def test_root_post_error_handling(client):
    """Test POST / handles job_manager errors."""
    with patch('src.jobs.manager.job_manager') as mock_manager:
        mock_manager.enqueue_scraper.side_effect = Exception("Redis connection failed")
        
        response = client.post("/", data={"action": "scrape"}, follow_redirects=False)
        
        # Should handle error gracefully
        assert response.status_code in [303, 500]
