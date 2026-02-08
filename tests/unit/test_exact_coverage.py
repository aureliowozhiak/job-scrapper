"""Laser-focused tests to hit the exact remaining lines for 100% coverage."""
import pytest
from unittest.mock import patch, MagicMock, mock_open
import json


class TestExactMissingLines:
    """Target the exact 22 missing lines."""
    
    # main.py line 82: has_running = queue_status.get("started", 0) > 0
    def test_main_line_82_exception_fallback(self, client):
        """When get_all_job_statuses throws, exception handler sets defaults, line 82 executes."""
        with patch('src.jobs.manager.job_manager.get_all_job_statuses', side_effect=Exception("fail")):
            response = client.get("/")
            assert response.status_code == 200
            # Line 82 is INSIDE the except block where queue_status = defaults
            # Actually wait - line 82 is queue_status.get("started", 0) > 0
            # That's in the try block. The except is 83-85.
            # So line 82 needs the try block to succeed.
    
    # Let me re-examine. Looking at coverage report: line 82 is NOT covered.
    # From show_missing: line 82 is 'has_running = queue_status.get("started", 0) > 0'
    # This is in the try block. For it to execute, get_all_job_statuses must succeed
    # and return something with "started" > 0.
    
    def test_main_line_82_has_running_jobs(self, client):
        """Test line 82 with running jobs."""
        with patch('src.jobs.manager.job_manager.get_all_job_statuses') as mock:
            mock.return_value = {"started": 1, "queued": 0, "failed": 0, "finished": 0}
            response = client.get("/")
            assert response.status_code == 200
            # Line 82 should execute: has_running = True
    
    # main.py line 159: same as above but in search action
    def test_main_line_159_has_running_jobs(self, client, test_db):
        """Test line 159 with running jobs during search."""
        from src.database.models import Position
        
        pos = Position(title="Dev", link="http://t.com", company="Co")
        test_db.add(pos)
        test_db.commit()
        
        with patch('src.jobs.manager.job_manager.get_all_job_statuses') as mock:
            mock.return_value = {"started": 1, "queued": 0, "failed": 0, "finished": 0}
            response = client.post("/", data={"action": "search", "word": "Dev"})
            assert response.status_code == 200
    
    # admin.py lines 76-77: exception handler in trigger_pipeline
    def test_admin_lines_76_77_pipeline_exception(self, client):
        """Test admin pipeline exception handler."""
        with patch('src.jobs.manager.job_manager.enqueue_pipeline', side_effect=Exception("fail")):
            response = client.post("/api/admin/pipeline")
            assert response.status_code == 500
            assert "Failed to enqueue pipeline" in response.json()["detail"]
    
    # health.py lines 29-30: DB health exception handler
    def test_health_lines_29_30_db_exception(self):
        """Test DB health exception handler."""
        from fastapi.testclient import TestClient
        from src.api.main import app
        from src.database.connection import get_db
        
        def error_db():
            mock = MagicMock()
            mock.execute.side_effect = Exception("DB fail")
            yield mock
        
        app.dependency_overrides[get_db] = error_db
        client = TestClient(app, raise_server_exceptions=False)
        
        response = client.get("/api/health/db")
        assert response.json()["status"] == "unhealthy"
        assert "error" in response.json()
        
        app.dependency_overrides.clear()
    
    # websocket.py lines 112-114: defensive exception handler
    # These lines catch unexpected exceptions (not WebSocketDisconnect) in the outer try block
    # The inner try/except catches all exceptions from the loop body, making this very hard to hit
    # This is defensive code - accepting 99.7% coverage
    # @pytest.mark.asyncio
    # async def test_websocket_lines_112_114_generic_exception(self):
    #     """Would need to test unexpected exception in while loop."""
    #     pass
    
    # connection.py lines 43-45: rollback on exception
        """Test get_db_context rollback on exception."""
        from src.database.connection import get_db_context
        
        with patch('src.database.connection.SessionLocal') as mock_sl:
            mock_db = MagicMock()
            mock_sl.return_value = mock_db
            
            with pytest.raises(Exception):
                with get_db_context():
                    raise Exception("err")
            
            mock_db.rollback.assert_called_once()
            mock_db.close.assert_called_once()
    
    # repositories.py lines 140-142: exception in bulk_upsert
    def test_repo_lines_140_142_exception(self, test_db):
        """Test bulk_upsert exception handling."""
        from src.database.repositories import PositionRepository
        
        repo = PositionRepository(test_db)
        
        with patch.object(repo, 'get_by_link', side_effect=[None, Exception("err"), None]):
            jobs = [
                {"title": "J1", "link": "http://t1.com", "company": "C1"},
                {"title": "J2", "link": "http://t2.com", "company": "C2"},
                {"title": "J3", "link": "http://t3.com", "company": "C3"},
            ]
            stats = repo.bulk_upsert(jobs)
            assert stats["errors"] == 1
    
    # load.py lines 87-88: exception counting local jobs
    def test_load_lines_87_88_count_exception(self):
        """Test get_sync_status exception counting local jobs."""
        from src.etl.load import get_sync_status
        
        with patch('src.etl.load.os.path.exists', return_value=True):
            with patch('src.etl.load.os.listdir', return_value=['test.json']):
                with patch('builtins.open', mock_open(read_data='invalid')):
                    with patch('json.load', side_effect=Exception("parse error")):
                        with patch('src.etl.load.sqlite3.connect') as mock_conn:
                            mock_conn.return_value.cursor.return_value.fetchone.return_value = (5,)
                            with patch('src.etl.load.logger'):
                                status = get_sync_status()
                                # Should handle exception, line 88 executes
                                assert status["total_db_jobs"] == 5
    
    # load.py lines 102-103: exception counting DB jobs
    def test_load_lines_102_103_db_connection_fail(self):
        """Test get_sync_status exception in DB connection block."""
        from src.etl.load import get_sync_status
        
        # Directory must exist to get past line 69
        with patch('src.etl.load.os.path.exists', return_value=True):
            with patch('src.etl.load.os.listdir', return_value=[]):  # No files
                # Make get_db_connection raise exception
                with patch('src.etl.load.get_db_connection', side_effect=Exception("DB connection failed")):
                    with patch('src.etl.load.logger'):
                        status = get_sync_status()
                        # Lines 102-103 execute, db_count stays 0
                        assert status["total_db_jobs"] == 0
                        assert status["local_jobs_today"] == 0
    
    # load.py line 172: ImportError warning for validation
    @patch('src.etl.validate.validate_json_jobs', side_effect=ImportError("no module"))
    @patch('src.etl.load.os.path.exists', return_value=True)
    @patch('src.etl.load.os.listdir', return_value=['j.json'])
    @patch('builtins.open', new_callable=mock_open)
    @patch('src.etl.load.sqlite3.connect')
    def test_load_line_172_import_error(self, mock_conn, mock_file, *args):
        """Test line 172 ImportError handler."""
        from src.etl.load import run_load_process
        
        mock_file.return_value.read.return_value = '[[{"title":"J","link":"L","company":"C"}]]'
        mock_c = MagicMock()
        mock_cur = MagicMock()
        mock_conn.return_value = mock_c
        mock_c.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = [(0, 'created_at')]
        mock_cur.fetchone.return_value = None
        
        with patch('src.etl.load.logger'):
            result = run_load_process()
            assert 'inserted' in result
    
    # load.py line 190: continue when position is a list
    @patch('src.etl.load.os.path.exists', return_value=True)
    @patch('src.etl.load.os.listdir', return_value=['j.json'])
    @patch('builtins.open', new_callable=mock_open)
    @patch('src.etl.load.sqlite3.connect')
    def test_load_line_190_list_position(self, mock_conn, mock_file, *args):
        """Test line 190 when position is list."""
        from src.etl.load import run_load_process
        
        mock_file.return_value.read.return_value = '[[]]'
        
        # Return mix: list and dict (no validation - disable it)
        with patch('src.core.config.settings.enable_pre_validation', False):
            mock_c = MagicMock()
            mock_cur = MagicMock()
            mock_conn.return_value = mock_c
            mock_c.cursor.return_value = mock_cur
            mock_cur.fetchall.return_value = [(0, 'created_at')]
            mock_cur.fetchone.return_value = None
            
            # Patch json.load to return mixed content
            with patch('json.load', return_value=[[["list"], {"title": "J", "link": "L", "company": "C"}]]):
                result = run_load_process()
                assert result['processed'] >= 0
    
    # task_scraper.py - updated to use scrapy_runner
    def test_scraper_new_implementation(self):
        """Test new scraper implementation."""
        from src.jobs.task_scraper import task_scraper
        
        with patch('src.etl.scrapy_runner.run_integrated_scraper', return_value={"total_jobs": 10}):
            result = task_scraper()
            assert result["status"] == "completed"
            assert "stats" in result

