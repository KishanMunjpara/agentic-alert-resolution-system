"""
WebSocket Connection Manager
Manages WebSocket connections and broadcasts events to connected clients
"""

import logging
from typing import List, Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time event broadcasting
    """
    
    def __init__(self):
        """Initialize connection manager"""
        self.active_connections: List[WebSocket] = []
        self.logger = logging.getLogger(__name__)
    
    async def connect(self, websocket: WebSocket):
        """
        Accept and register a new WebSocket connection
        
        Args:
            websocket: WebSocket connection to add
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        self.logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection
        
        Args:
            websocket: WebSocket connection to remove
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, event_type: str, data: dict):
        """
        Broadcast an event to all connected WebSocket clients
        
        Args:
            event_type: Type of event (e.g., "investigation_started", "decision_made")
            data: Event data dictionary
        """
        if not self.active_connections:
            return
        
        message = {
            "event": event_type,
            "timestamp": None,  # Will be set by caller if needed
            "data": data
        }
        
        # Send to all active connections
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                self.logger.error(f"Failed to send WebSocket message to connection: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for connection in disconnected:
            self.disconnect(connection)
    
    def get_connection_count(self) -> int:
        """
        Get the number of active WebSocket connections
        
        Returns:
            Number of active connections
        """
        return len(self.active_connections)


# Singleton instance
_manager_instance: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """
    Get or create the singleton ConnectionManager instance
    
    Returns:
        ConnectionManager instance
    """
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = ConnectionManager()
    return _manager_instance

