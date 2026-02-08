"""Final polish tests for 100% coverage."""
import pytest
from unittest.mock import patch, MagicMock, mock_open
import json
import os
from fastapi.testclient import TestClient
from src.api.main import app

class TestFinalPolish:
    @pytest.mark.asyncio
    async def test_websocket_lines_112_114_exception(self):
        """Cover websocket.py:112-114 exception handler."""
        from src.api.routes.websocket import websocket_job_status
        from unittest.mock import AsyncMock
        
        mock_ws = AsyncMock()
        # Trigger exception inside the try block
        mock_ws.accept.side_effect = Exception("WS fail")
        
        with patch('builtins.print') as mock_print:
            await websocket_job_status(mock_ws, "id")
            assert mock_print.called

    def test_load_line_80_not_list(self):
        """Cover load.py:80 branch where data is not a list."""
        from src.etl.load import get_sync_status
        with patch('src.etl.load.get_current_json_directory', return_value="out"):
            with patch('os.path.exists', return_value=True):
                with patch('os.listdir', return_value=['f.json']):
                    # data is NOT a list
                    with patch('builtins.open', mock_open(read_data='{"not": "a list"}')):
                        with patch('src.etl.load.get_db_connection'):
                            get_sync_status()
                            # This hits the branch 80->76

    def test_load_line_139_not_list(self):
        """Cover load.py:139 branch where data is not a list."""
        from src.etl.load import run_load_process
        with patch('src.etl.load.get_current_json_directory', return_value="out"):
            with patch('os.path.exists', return_value=True):
                with patch('os.listdir', return_value=['f.json']):
                    # data is NOT a list
                    with patch('builtins.open', mock_open(read_data='{"not": "a list"}')):
                        with patch('src.etl.load.get_db_connection'):
                             run_load_process()
                             # This hits the branch 139->131
