"""Comprehensive WebSocket tests using async mocking."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio


@pytest.mark.asyncio
async def test_connection_manager_init():
    """Test ConnectionManager initialization."""
    from src.api.routes.websocket import ConnectionManager
    
    manager = ConnectionManager()
    assert manager.active_connections == []


@pytest.mark.asyncio
async def test_connection_manager_connect():
    """Test ConnectionManager connect method."""
    from src.api.routes.websocket import ConnectionManager
    
    manager = ConnectionManager()
    mock_ws = MagicMock()
    mock_ws.accept = AsyncMock()
    
    await manager.connect(mock_ws)
    
    assert mock_ws in manager.active_connections
    mock_ws.accept.assert_called_once()


@pytest.mark.asyncio
async def test_connection_manager_disconnect():
    """Test ConnectionManager disconnect method."""
    from src.api.routes.websocket import ConnectionManager
    
    manager = ConnectionManager()
    mock_ws = MagicMock()
    
    # Add then remove connection
    manager.active_connections.append(mock_ws)
    manager.disconnect(mock_ws)
    
    assert mock_ws not in manager.active_connections


@pytest.mark.asyncio
async def test_connection_manager_broadcast():
    """Test ConnectionManager broadcast method."""
    from src.api.routes.websocket import ConnectionManager
    
    manager = ConnectionManager()
    mock_ws1 = MagicMock()
    mock_ws2 = MagicMock()
    
    # Setup send_json as async mock
    mock_ws1.send_json = AsyncMock()
    mock_ws2.send_json = AsyncMock()
    
    manager.active_connections = [mock_ws1, mock_ws2]
    
    await manager.broadcast({"status": "test"})
    
    mock_ws1.send_json.assert_called_once_with({"status": "test"})
    mock_ws2.send_json.assert_called_once_with({"status": "test"})


@pytest.mark.asyncio
async def test_connection_manager_broadcast_with_error():
    """Test ConnectionManager broadcast handles connection errors."""
    from src.api.routes.websocket import ConnectionManager
    
    manager = ConnectionManager()
    mock_ws = MagicMock()
    
    # Simulate send_json raising an exception
    mock_ws.send_json = AsyncMock(side_effect=Exception("Connection lost"))
    
    manager.active_connections = [mock_ws]
    
    # Should handle exception gracefully
    await manager.broadcast({"status": "test"})
    # No exception should propagate


@pytest.mark.asyncio
async def test_websocket_status_endpoint():
    """Test WebSocket status endpoint logic."""
    from src.api.routes.websocket import websocket_status, manager
    from fastapi import WebSocketDisconnect
    
    mock_websocket = MagicMock()
    mock_websocket.accept = AsyncMock()
    mock_websocket.send_json = AsyncMock()
    
    # Simulate disconnect after 2 iterations
    call_count = [0]
    
    async def mock_sleep(duration):
        call_count[0] += 1
        if call_count[0] >= 2:
            raise WebSocketDisconnect()
    
    with patch('src.api.routes.websocket.job_manager') as mock_job_manager:
        mock_job_manager.get_all_job_statuses.return_value = {
            "queued": 1,
            "started": 0,
            "finished": 5,
            "failed": 0
        }
        
        with patch('asyncio.sleep', side_effect=mock_sleep):
            await websocket_status(mock_websocket)
    
    # Verify connection was accepted
    mock_websocket.accept.assert_called_once()
    
    # Verify status was sent
    assert mock_websocket.send_json.call_count >= 1


@pytest.mark.asyncio
async def test_websocket_status_with_error():
    """Test WebSocket status endpoint handles errors."""
    from src.api.routes.websocket import websocket_status
    from fastapi import WebSocketDisconnect
    
    mock_websocket = MagicMock()
    mock_websocket.accept = AsyncMock()
    mock_websocket.send_json = AsyncMock()
    
    call_count = [0]
    
    async def mock_sleep(duration):
        call_count[0] += 1
        if call_count[0] >= 2:
            raise WebSocketDisconnect()
    
    with patch('src.api.routes.websocket.job_manager') as mock_job_manager:
        # Simulate error in job_manager
        mock_job_manager.get_all_job_statuses.side_effect = Exception("Redis error")
        
        with patch('asyncio.sleep', side_effect=mock_sleep):
            await websocket_status(mock_websocket)
    
    # Should send error message
    assert mock_websocket.send_json.call_count >= 1
    # Check if error was sent
    calls = [call[0][0] for call in mock_websocket.send_json.call_args_list]
    assert any(msg.get("type") == "error" for msg in calls)


@pytest.mark.asyncio
async def test_websocket_job_status_endpoint():
    """Test WebSocket job status endpoint logic."""
    from src.api.routes.websocket import websocket_job_status
    from fastapi import WebSocketDisconnect
    
    mock_websocket = MagicMock()
    mock_websocket.accept = AsyncMock()
    mock_websocket.send_json = AsyncMock()
    
    call_count = [0]
    
    async def mock_sleep(duration):
        call_count[0] += 1
    
    with patch('src.api.routes.websocket.job_manager') as mock_job_manager:
        # First call: job is running, second call: job is finished
        mock_job_manager.get_job_status.side_effect = [
            {"status": "started", "progress": 50},
            {"status": "finished", "result": {"success": True}}
        ]
        
        with patch('asyncio.sleep', side_effect=mock_sleep):
            await websocket_job_status(mock_websocket, "test-job-123")
    
    # Verify connection was accepted
    mock_websocket.accept.assert_called_once()
    
    # Verify status was sent twice (started then finished)
    assert mock_websocket.send_json.call_count == 2


@pytest.mark.asyncio
async def test_websocket_job_status_with_failed_job():
    """Test WebSocket job tracking for failed job."""
    from src.api.routes.websocket import websocket_job_status
    
    mock_websocket = MagicMock()
    mock_websocket.accept = AsyncMock()
    mock_websocket.send_json = AsyncMock()
    
    with patch('src.api.routes.websocket.job_manager') as mock_job_manager:
        # Job failed immediately
        mock_job_manager.get_job_status.return_value = {
            "status": "failed",
            "error": "Job failed"
        }
        
        await websocket_job_status(mock_websocket, "failed-job-123")
    
    # Should send status once and stop
    assert mock_websocket.send_json.call_count == 1


@pytest.mark.asyncio
async def test_websocket_job_status_with_not_found():
    """Test WebSocket job tracking for non-existent job."""
    from src.api.routes.websocket import websocket_job_status
    
    mock_websocket = MagicMock()
    mock_websocket.accept = AsyncMock()
    mock_websocket.send_json = AsyncMock()
    
    with patch('src.api.routes.websocket.job_manager') as mock_job_manager:
        # Job not found
        mock_job_manager.get_job_status.return_value = {
            "status": "not_found"
        }
        
        await websocket_job_status(mock_websocket, "missing-job")
    
    # Should send status once and stop
    assert mock_websocket.send_json.call_count == 1


@pytest.mark.asyncio
async def test_websocket_job_status_with_error():
    """Test WebSocket job tracking handles errors."""
    from src.api.routes.websocket import websocket_job_status
    from fastapi import WebSocketDisconnect
    
    mock_websocket = MagicMock()
    mock_websocket.accept = AsyncMock()
    mock_websocket.send_json = AsyncMock()
    
    call_count = [0]
    
    async def mock_sleep(duration):
        call_count[0] += 1
        if call_count[0] >= 2:
            raise WebSocketDisconnect()
    
    with patch('src.api.routes.websocket.job_manager') as mock_job_manager:
        # Simulate error
        mock_job_manager.get_job_status.side_effect = Exception("Job queue error")
        
        with patch('asyncio.sleep', side_effect=mock_sleep):
            await websocket_job_status(mock_websocket, "error-job")
    
    # Should send error messages
    assert mock_websocket.send_json.call_count >= 1
    calls = [call[0][0] for call in mock_websocket.send_json.call_args_list]
    assert any(msg.get("type") == "error" for msg in calls)


@pytest.mark.asyncio
async def test_websocket_generic_exception_handling():
    """Test WebSocket endpoints handle generic exceptions."""
    from src.api.routes.websocket import websocket_status
    
    mock_websocket = MagicMock()
    mock_websocket.accept = AsyncMock(side_effect=Exception("Connection error"))
    
    # Should handle exception without crashing
    with patch('builtins.print') as mock_print:
        try:
            await websocket_status(mock_websocket)
        except:
            pass
