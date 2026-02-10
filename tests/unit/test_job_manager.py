"""Unit tests for job manager."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from src.jobs.manager import JobManager


@pytest.fixture
def mock_redis():
    """Mock Redis connection."""
    return Mock()


@pytest.fixture  
def mock_queue():
    """Mock RQ queue."""
    queue = Mock()
    queue.enqueue = Mock()
    return queue


@pytest.fixture
def job_manager_mock(mock_redis, mock_queue):
    """Create JobManager with mocked dependencies."""
    with patch('src.jobs.manager.Redis') as MockRedis, \
         patch('src.jobs.manager.Queue') as MockQueue:
        MockRedis.from_url.return_value = mock_redis
        MockQueue.return_value = mock_queue
        
        manager = JobManager()
        manager.redis = mock_redis
        manager.queue = mock_queue
        
        yield manager


def test_enqueue_scraper(job_manager_mock):
    """Test enqueueing scraper job."""
    mock_job = Mock()
    mock_job.id = "scraper-test-123"
    job_manager_mock.queue.enqueue.return_value = mock_job
    
    job_id = job_manager_mock.enqueue_scraper()
    
    assert job_id == "scraper-test-123"
    assert job_manager_mock.queue.enqueue.called


def test_enqueue_loader(job_manager_mock):
    """Test enqueueing loader job."""
    mock_job = Mock()
    mock_job.id = "loader-test-123"
    job_manager_mock.queue.enqueue.return_value = mock_job
    
    job_id = job_manager_mock.enqueue_loader()
    
    assert job_id == "loader-test-123"
    assert job_manager_mock.queue.enqueue.called


def test_enqueue_validator(job_manager_mock):
    """Test enqueueing validator job."""
    mock_job = Mock()
    mock_job.id = "validator-test-123"
    job_manager_mock.queue.enqueue.return_value = mock_job
    
    job_id = job_manager_mock.enqueue_validator()
    
    assert job_id == "validator-test-123"
    assert job_manager_mock.queue.enqueue.called


def test_enqueue_sync_check(job_manager_mock):
    """Test enqueueing sync check job."""
    mock_job = Mock()
    mock_job.id = "sync-test-123"
    job_manager_mock.queue.enqueue.return_value = mock_job
    
    job_id = job_manager_mock.enqueue_sync_check()
    
    assert job_id == "sync-test-123"
    assert job_manager_mock.queue.enqueue.called


def test_enqueue_pipeline(job_manager_mock):
    """Test enqueueing full pipeline with dependencies (scrape, validate, load, cleanup)."""
    mock_jobs = [
        Mock(id="pipeline-20260210123456-scrape"),
        Mock(id="pipeline-20260210123456-validate"),
        Mock(id="pipeline-20260210123456-load"),
        Mock(id="pipeline-20260210123456-cleanup")
    ]
    job_manager_mock.pipeline_queue.enqueue.side_effect = mock_jobs
    
    job_ids = job_manager_mock.enqueue_pipeline()
    
    assert len(job_ids) == 4
    assert "scrape" in job_ids[0]
    assert "validate" in job_ids[1]
    assert "load" in job_ids[2]
    assert "cleanup" in job_ids[3]
    assert job_manager_mock.pipeline_queue.enqueue.call_count == 4


def test_get_job_status_success(job_manager_mock):
    """Test getting job status for successful job."""
    with patch('src.jobs.manager.Job') as MockJob:
        mock_job = Mock()
        mock_job.id = "test-123"
        mock_job.get_status.return_value = "finished"
        mock_job.result = {"status": "completed"}
        mock_job.started_at = None
        mock_job.ended_at = None
        mock_job.is_failed = False
        MockJob.fetch.return_value = mock_job
        
        status = job_manager_mock.get_job_status("test-123")
        
        assert status["id"] == "test-123"
        assert status["status"] == "finished"


def test_get_job_status_not_found(job_manager_mock):
    """Test getting job status for non-existent job."""
    with patch('src.jobs.manager.Job') as MockJob:
        MockJob.fetch.side_effect = Exception("Job not found")
        
        status = job_manager_mock.get_job_status("nonexistent")
        
        assert status["status"] == "not_found"
        assert "error" in status


def test_get_all_job_statuses(job_manager_mock):
    """Test getting all job statuses - now counts pipeline groups."""
    with patch('src.jobs.manager.StartedJobRegistry') as MockStarted, \
         patch('src.jobs.manager.FinishedJobRegistry') as MockFinished, \
         patch('src.jobs.manager.FailedJobRegistry') as MockFailed, \
         patch('src.jobs.manager.Job') as MockJob:
        
        # Mock registries
        mock_started_reg = Mock()
        mock_started_reg.get_job_ids.return_value = ["pipeline-20260210001122-scrape"]
        MockStarted.return_value = mock_started_reg
        
        mock_finished_reg = Mock()
        mock_finished_reg.get_job_ids.return_value = [
            "pipeline-20260209001122-scrape",
            "pipeline-20260209001122-validate",
            "pipeline-20260209001122-load",
            "pipeline-20260209001122-cleanup",
            "pipeline-20260209002233-scrape"
        ]
        MockFinished.return_value = mock_finished_reg
        
        mock_failed_reg = Mock()
        mock_failed_reg.get_job_ids.return_value = []
        MockFailed.return_value = mock_failed_reg
        
        job_manager_mock.queue.get_job_ids = Mock(return_value=[])
        job_manager_mock.pipeline_queue.get_job_ids = Mock(return_value=[])
        
        # Mock Job.fetch to return job statuses
        def mock_fetch(job_id, connection):
            mock_job = Mock()
            if "20260210001122" in job_id:
                mock_job.get_status.return_value = "started"
            else:
                mock_job.get_status.return_value = "finished"
            return mock_job
        
        MockJob.fetch.side_effect = mock_fetch
        
        statuses = job_manager_mock.get_all_job_statuses()
        
        # Should count pipeline groups, not individual tasks
        # 1 started pipeline (20260210001122)
        # 2 finished pipelines (20260209001122 and 20260209002233)
        assert statuses["started"] == 1
        assert statuses["finished"] == 2
        assert statuses["failed"] == 0


def test_cancel_job_success(job_manager_mock):
    """Test cancelling a job successfully."""
    with patch('src.jobs.manager.Job') as MockJob:
        mock_job = Mock()
        mock_job.cancel = Mock()
        MockJob.fetch.return_value = mock_job
        
        result = job_manager_mock.cancel_job("test-123")
        
        assert result is True
        mock_job.cancel.assert_called_once()


def test_cancel_job_not_found(job_manager_mock):
    """Test cancelling non-existent job."""
    with patch('src.jobs.manager.Job') as MockJob:
        MockJob.fetch.side_effect = Exception("Not found")
        
        result = job_manager_mock.cancel_job("nonexistent")
        
        assert result is False


def test_clear_failed_jobs(job_manager_mock):
    """Test clearing failed jobs."""
    with patch('src.jobs.manager.FailedJobRegistry') as MockFailed:
        mock_registry = Mock()
        mock_registry.get_job_ids.return_value = ["failed-1", "failed-2"]
        mock_registry.remove = Mock()
        MockFailed.return_value = mock_registry
        
        job_manager_mock.clear_failed_jobs()
        
        # Should call remove for each failed job
        assert mock_registry.remove.call_count == 2

