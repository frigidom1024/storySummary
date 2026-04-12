"""WebSocket connection manager for real-time progress updates."""
from fastapi import WebSocket
from typing import Dict, Set
import json


class ConnectionManager:
    """Manages WebSocket connections per book."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.connections: Dict[str, Set[WebSocket]] = {}
        return cls._instance

    async def connect(self, book_id: str, websocket: WebSocket):
        await websocket.accept()
        if book_id not in self.connections:
            self.connections[book_id] = set()
        self.connections[book_id].add(websocket)

    def disconnect(self, book_id: str, websocket: WebSocket):
        if book_id in self.connections:
            self.connections[book_id].discard(websocket)
            if not self.connections[book_id]:
                del self.connections[book_id]

    async def send_progress(self, book_id: str, progress: int, message: str, status: str = "processing"):
        """Send progress update to all clients watching this book."""
        if book_id not in self.connections:
            return
        payload = json.dumps({
            "progress": progress,
            "message": message,
            "status": status
        })
        disconnected = set()
        for websocket in self.connections[book_id]:
            try:
                await websocket.send_text(payload)
            except Exception:
                disconnected.add(websocket)
        for ws in disconnected:
            self.connections[book_id].discard(ws)


# Singleton instance
manager = ConnectionManager()
