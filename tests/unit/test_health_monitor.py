"""Tests for health monitoring functionality."""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session
from src.core.health_monitor import HealthMonitor
from src.schemas.health import ScraperMetrics, SystemHealth, HealthDashboardResponse


class TestHealthMonitor:
    """Test health monitoring service."""
    
    @pytest.fixture
    def health_monitor(self):
        """Create health monitor instance."""
        return HealthMonitor()
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = Mock(spec=Session)
        return db
    
    def test_health_monitor_initialization(self, health_monitor):
        """Test health monitor initializes correctly."""
        assert health_monitor.spider_config is not None
        assert len(health_monitor.spider_config) > 0
    
    def test_get_scraper_metrics(self, health_monitor, mock_db):
        """Test getting scraper metrics."""
        # Mock database queries - return integers
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = 100
        mock_db.query.return_value = mock_query
        
        metrics = health_monitor.get_scraper_metrics(mock_db)
        
        assert isinstance(metrics, list)
        assert len(metrics) > 0
        assert all(isinstance(m, ScraperMetrics) for m in metrics)
        
        # Check first metric has expected fields
        first_metric = metrics[0]
        assert first_metric.scraper_id is not None
        assert first_metric.scraper_name is not None
        assert first_metric.domain is not None
        assert isinstance(first_metric.is_active, bool)
        assert isinstance(first_metric.total_jobs_scraped, int)
    
    def test_get_system_health(self, health_monitor, mock_db):
        """Test getting system health."""
        # Mock database execute
        mock_db.execute.return_value = Mock()
        mock_db.query().scalar.return_value = 500
        
        with patch('src.core.health_monitor.Redis') as mock_redis:
            mock_redis.from_url().ping.return_value = True
            
            with patch('src.core.health_monitor.job_manager') as mock_manager:
                mock_manager.get_all_job_statuses.return_value = {
                    'queued': 5,
                    'started': 2,
                    'finished': 100,
                    'failed': 1
                }
                
                health = health_monitor.get_system_health(mock_db)
                
                assert isinstance(health, SystemHealth)
                assert health.status in ['healthy', 'degraded', 'unhealthy']
                assert health.database_status == 'connected'
                assert health.redis_status == 'connected'
                assert isinstance(health.queue_status, dict)
                assert health.total_jobs == 500
    
    def test_get_dashboard_data(self, health_monitor):
        """Test getting complete dashboard data."""
        with patch('src.core.health_monitor.SessionLocal') as mock_session:
            mock_db = Mock(spec=Session)
            mock_session.return_value.__enter__.return_value = mock_db
            
            # Mock queries properly
            mock_query = Mock()
            mock_query.filter.return_value = mock_query
            mock_query.scalar.return_value = 50
            mock_db.query.return_value = mock_query
            mock_db.execute.return_value = Mock()
            
            with patch('src.core.health_monitor.Redis') as mock_redis:
                mock_redis.from_url().ping.return_value = True
                
                with patch('src.core.health_monitor.job_manager') as mock_manager:
                    mock_manager.get_all_job_statuses.return_value = {
                        'queued': 0,
                        'started': 0,
                        'finished': 50,
                        'failed': 0
                    }
                    
                    dashboard = health_monitor.get_dashboard_data()
                    
                    assert isinstance(dashboard, HealthDashboardResponse)
                    assert isinstance(dashboard.system, SystemHealth)
                    assert isinstance(dashboard.scrapers, list)
                    assert len(dashboard.scrapers) > 0
    
    def test_system_health_unhealthy_database(self, health_monitor, mock_db):
        """Test system reports unhealthy when database is down."""
        # Mock database failure
        mock_db.execute.side_effect = Exception("Database connection failed")
        mock_db.query().scalar.return_value = 0
        
        with patch('src.core.health_monitor.Redis') as mock_redis:
            mock_redis.from_url().ping.return_value = True
            
            with patch('src.core.health_monitor.job_manager') as mock_manager:
                mock_manager.get_all_job_statuses.return_value = {
                    'queued': 0, 'started': 0, 'finished': 0, 'failed': 0
                }
                
                health = health_monitor.get_system_health(mock_db)
                
                assert health.status == 'unhealthy'
                assert 'error' in health.database_status.lower()
    
    def test_system_health_degraded_with_failures(self, health_monitor, mock_db):
        """Test system reports degraded when many jobs fail."""
        mock_db.execute.return_value = Mock()
        mock_db.query().scalar.return_value = 100
        
        with patch('src.core.health_monitor.Redis') as mock_redis:
            mock_redis.from_url().ping.return_value = True
            
            with patch('src.core.health_monitor.job_manager') as mock_manager:
                mock_manager.get_all_job_statuses.return_value = {
                    'queued': 0,
                    'started': 0,
                    'finished': 10,
                    'failed': 10  # More than 5 failures
                }
                
                health = health_monitor.get_system_health(mock_db)
                
                assert health.status == 'degraded'
                assert health.queue_status['failed'] == 10


@pytest.mark.asyncio
class TestHealthAPIEndpoints:
    """Test health monitoring API endpoints."""
    
    def test_health_dashboard_endpoint(self, client):
        """Test health dashboard API endpoint."""
        with patch('src.api.routes.health.health_monitor') as mock_monitor:
            # Mock response data
            mock_monitor.get_dashboard_data.return_value = HealthDashboardResponse(
                system=SystemHealth(
                    status='healthy',
                    timestamp=datetime.now(timezone.utc),
                    database_status='connected',
                    redis_status='connected',
                    queue_status={'queued': 0, 'running': 0, 'finished': 50, 'failed': 0},
                    total_jobs=500,
                    total_scrapers=4,
                    active_scrapers=4
                ),
                scrapers=[
                    ScraperMetrics(
                        scraper_id='test_spider',
                        scraper_name='Test Spider',
                        domain='test.com',
                        is_active=True,
                        total_jobs_scraped=100,
                        success_rate_24h=95.0
                    )
                ]
            )
            
            response = client.get('/api/health/dashboard')
            
            assert response.status_code == 200
            data = response.json()
            assert 'system' in data
            assert 'scrapers' in data
            assert data['system']['status'] == 'healthy'
            assert len(data['scrapers']) > 0
