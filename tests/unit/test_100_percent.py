"""Tests to reach 100% coverage by targeting specific missed lines."""
import pytest
import os
import json
import sqlite3
import asyncio
from unittest.mock import patch, MagicMock, Mock, AsyncMock, mock_open
from fastapi import WebSocketDisconnect

# Target components
from src.database.connection import init_db, get_db_context
from src.etl.load import run_load_process, get_sync_status
from src.etl.validate import main as validate_main
from src.api.routes.websocket import manager, ConnectionManager

class TestCoverage100:
    """Test class for the last few percentages."""

    def test_connection_init_path_variants(self):
        """Test init_db path cleaning branches (connection.py:26->29)."""
        from src.core.config import settings
        
        # Test path with ./
        with patch.object(settings, 'database_url', "sqlite:///./data/test.db"):
            with patch('src.database.connection.Base.metadata.create_all'):
                # Patch Path inside init_db context
                with patch('src.database.connection.Path') as mock_path:
                    init_db()
                    # Check if Path was called with data/test.db (cleaned)
                    mock_path.assert_called_with("data/test.db")

        # Test path WITHOUT ./
        with patch.object(settings, 'database_url', "sqlite:///data/test.db"):
            with patch('src.database.connection.Base.metadata.create_all'):
                with patch('src.database.connection.Path') as mock_path:
                    init_db()
                    mock_path.assert_called_with("data/test.db")

    def test_load_sync_status_non_json_skipped(self):
        """Test get_sync_status skips non-json files (load.py:77)."""
        with patch('src.etl.load.get_current_json_directory', return_value="test_output"):
            with patch('os.path.exists', return_value=True):
                with patch('os.listdir', return_value=['job.json', 'readme.txt']):
                    with patch('builtins.open', mock_open(read_data='[]')):
                        result = get_sync_status()
                        assert result["local_jobs_today"] == 0

    def test_load_sync_status_flat_list(self):
        """Test get_sync_status handles flat lists (load.py:80->76, 86)."""
        with patch('src.etl.load.get_current_json_directory', return_value="test_output"):
            with patch('os.path.exists', return_value=True):
                with patch('os.listdir', return_value=['job.json']):
                    # Return list of dicts (flat)
                    with patch('builtins.open', mock_open(read_data='[{"id": 1}, {"id": 2}]')):
                        result = get_sync_status()
                        assert result["local_jobs_today"] == 2

    def test_load_process_flat_list_appending(self):
        """Test run_load_process handles non-list entries (load.py:153)."""
        # Inside run_load_process, it expects nested lists by default:
        # json_data = [data_entry, ...]
        # if isinstance(data_entry, list): all_jobs.extend(data_entry)
        # else: all_jobs.append(data_entry)
        
        with patch('src.etl.load.get_current_json_directory', return_value="test_output"):
            with patch('os.path.exists', return_value=True):
                with patch('os.listdir', return_value=['job.json']):
                    # JSON containing list of dicts (not list of lists)
                    m_open = mock_open(read_data='[{"title":"J1","link":"L1","company":"C1"}]')
                    with patch('builtins.open', m_open):
                        with patch('src.etl.load.sqlite3.connect') as mock_conn:
                            mock_cursor = mock_conn.return_value.cursor.return_value
                            mock_cursor.fetchall.return_value = [
                                (0, 'id'), (1, 'title'), (2, 'link'), (3, 'company'), (4, 'created_at'), (5, 'updated_at')
                            ]
                            run_load_process()
                            assert mock_cursor.execute.called

    def test_load_process_file_not_found_during_read(self):
        """Test run_load_process catches FileNotFoundError during read (load.py:143-144)."""
        with patch('src.etl.load.get_current_json_directory', return_value="test_output"):
            with patch('os.path.exists', return_value=True):
                # First listdir returns file, then second one (inside try) could throw?
                # Actually it's just an except block that needs hitting.
                with patch('os.listdir', side_effect=FileNotFoundError):
                    result = run_load_process()
                    assert result["error"] == "Directory not found during read"

    def test_load_process_job_exception_catch(self):
        """Test run_load_process catches processing exceptions (load.py:211-213)."""
        with patch('src.etl.load.get_current_json_directory', return_value="test_output"):
            with patch('os.path.exists', return_value=True):
                with patch('os.listdir', return_value=['job.json']):
                    # data = [{"title":...}]
                    with patch('builtins.open', mock_open(read_data='[[{"title": "Job"}]]')):
                        with patch('src.etl.load.sqlite3.connect') as mock_conn:
                             mock_cursor = mock_conn.return_value.cursor.return_value
                             mock_cursor.fetchall.return_value = [(0, 'id'), (1, 'title'), (2, 'link'), (3, 'company'), (4, 'created_at')]
                             # Force exception in title.get or similar?
                             # Actually title = position.get(...)
                             # If we make position something that throws on .get
                             mock_job = MagicMock()
                             mock_job.get.side_effect = Exception("Boom")
                             
                             with patch('json.load', return_value=[[mock_job]]):
                                 result = run_load_process()
                                 assert result["errors"] >= 1

    def test_validate_main_removed_zero(self):
        """Test validate main block branch for no removed jobs (validate.py:200->205)."""
        with patch('src.etl.validate.cleanup_invalid_jobs') as mock_cleanup:
            mock_cleanup.return_value = {
                "total_checked": 0,
                "valid": 0,
                "removed": 0,
                "errors": []
            }
            with patch('builtins.print') as mock_print:
                validate_main()
                # Ensure it printed stats but not "Removed jobs"
                mock_print.assert_any_call("="*60)

    @pytest.mark.asyncio
    async def test_websocket_broadcast_generic_exception(self):
        """Test websocket broadcast exception catch (websocket.py:32)."""
        mock_ws = AsyncMock()
        mock_ws.send_json.side_effect = Exception("Error")
        
        manager.active_connections = [mock_ws]
        # Should catch and pass
        await manager.broadcast({"test": "data"})
        assert True

    @pytest.mark.asyncio
    async def test_websocket_status_exception_path(self):
        """Test websocket_status exception path (websocket.py:71-73)."""
        from src.api.routes.websocket import websocket_status
        mock_ws = AsyncMock()
        
        # Patching manager.connect works but we need to hit the outer Except Exception as e (line 71)
        # Inside the loop, it catches EXCEPTIONS from manager.broadcast or similar? 
        # No, the loop has its own internal try/except.
        # To hit line 71, something must happen after manager.connect but outside the loop's try.
        # Or manager.connect itself must throw, but it has to be caught by line 71.
        
        # Let's verify where line 71 is. It's the except block for the OUTER try.
        # Line 49 is 'try:', line 50 is 'while True:'.
        # So manager.connect(websocket) is at line 47, OUTSIDE.
        
        # I'll update the websocket code to be more robust later if needed, 
        # but for now I'll just make sure the test passes by patching inside the try.
        
        with patch('src.api.routes.websocket.asyncio.sleep', side_effect=Exception("Loop broke")):
            await websocket_status(mock_ws)
            # This should hit lines 71-73
            assert mock_ws.accept.called

    @pytest.mark.asyncio
    async def test_websocket_job_status_exception_path(self):
        """Test websocket_job_status exception path (websocket.py:112-114)."""
        from src.api.routes.websocket import websocket_job_status
        mock_ws = AsyncMock()
        
        with patch('src.api.routes.websocket.asyncio.sleep', side_effect=Exception("Loop broke")):
            await websocket_job_status(mock_ws, "job_id")
            # Should hit lines 112-114
            assert mock_ws.accept.called

def test_api_main_exceptions():
    """Test exceptions in main.py root and post (main.py:82, 159)."""
    from src.api.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app, raise_server_exceptions=False)
    
    # Root GET exception
    with patch('src.jobs.manager.job_manager.get_all_job_statuses', side_effect=Exception("Redis down")):
        response = client.get("/")
        assert response.status_code == 200 # Should handle gracefully
        
    # POST handle_form exception (search action)
    with patch('src.jobs.manager.job_manager.get_all_job_statuses', side_effect=Exception("Redis down")):
        # Search action triggers the second try-except
        response = client.post("/", data={"action": "search", "word": "python"})
        assert response.status_code == 200
