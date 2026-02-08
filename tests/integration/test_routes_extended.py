"""Additional integration tests for API routes."""
import pytest
from unittest.mock import patch


def test_health_redis_check(client):
    """Test Redis health check endpoint."""
    with patch('src.api.routes.health.Redis') as MockRedis:
        mock_redis = MockRedis.from_url.return_value
        mock_redis.ping.return_value = True
        
        response = client.get("/api/health/redis")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["redis"] == "connected"


def test_health_redis_failure(client):
    """Test Redis health check when Redis is down."""
    with patch('src.api.routes.health.Redis') as MockRedis:
        mock_redis = MockRedis.from_url.return_value
        mock_redis.ping.side_effect = Exception("Connection refused")
        
        response = client.get("/api/health/redis")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
