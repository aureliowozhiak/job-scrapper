"""Tests for main.py root endpoint - updated for API-based architecture."""
import pytest
from unittest.mock import patch, MagicMock


def test_root_post_update_action(client):
    """Test POST / with action=update triggers pipeline."""
    with patch('src.jobs.manager.job_manager') as mock_manager:
        mock_manager.enqueue_pipeline.return_value = {"jobs": ["j1", "j2", "j3"]}
        
        response = client.post("/", data={"action": "update"}, follow_redirects=False)
        
        assert response.status_code == 303
        assert "msg=Pipeline" in response.headers["location"]
        mock_manager.enqueue_pipeline.assert_called_once()


def test_root_post_unknown_action(client):
    """Test POST / with unknown action."""
    response = client.post(
        "/",
        data={"action": "unknown_action"},
        follow_redirects=False
    )
    
    # Should redirect with error message
    assert response.status_code == 303
    assert "error=" in response.headers["location"]


def test_root_post_error_handling(client):
    """Test POST / handles job_manager errors."""
    with patch('src.jobs.manager.job_manager') as mock_manager:
        mock_manager.enqueue_pipeline.side_effect = Exception("Redis connection failed")
        
        response = client.post("/", data={"action": "update"}, follow_redirects=False)
        
        # Should handle error gracefully
        assert response.status_code == 303
        assert "error=" in response.headers["location"]
