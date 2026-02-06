"""WebSocket routes for real-time job status updates."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import asyncio
import json

from src.jobs.manager import job_manager

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """Accept and store WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                # Connection might be closed
                pass


manager = ConnectionManager()


@router.websocket("/ws/status")
async def websocket_status(websocket: WebSocket):
    """
    WebSocket endpoint for real-time job queue status updates.
    
    Sends queue status every 2 seconds to connected clients.
    """
    try:
        await manager.connect(websocket)
        while True:
            # Get current queue status
            try:
                queue_status = job_manager.get_all_job_statuses()
                
                # Send to client
                await websocket.send_json({
                    "type": "queue_status",
                    "data": queue_status
                })
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
            
            # Wait before next update
            await asyncio.sleep(2)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@router.websocket("/ws/job/{job_id}")
async def websocket_job_status(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for tracking a specific job's status.
    
    Sends job status updates every second until job completes or fails.
    """
    try:
        await manager.connect(websocket)
        while True:
            # Get job status
            try:
                status = job_manager.get_job_status(job_id)
                
                await websocket.send_json({
                    "type": "job_status",
                    "job_id": job_id,
                    "data": status
                })
                
                # Stop if job is finished
                if status.get("status") in ["finished", "failed", "not_found"]:
                    break
            
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
            
            # Wait before next update
            await asyncio.sleep(1)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)
