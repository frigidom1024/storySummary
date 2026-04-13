"""WebSocket connection manager for real-time progress updates."""
from fastapi import WebSocket
from typing import Dict, Set
from src.api.schemas.websocket import ProgressMessage, ProgressStatus, ProgressType
from src.logging_config import debug


class ConnectionManager:
    """Manages WebSocket connections per book."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.connections: Dict[str, Set[WebSocket]] = {}
        return cls._instance

    async def connect(self, book_id: str, websocket: WebSocket):
        debug("websocket", "book_id={} WebSocket connecting...", book_id)
        await websocket.accept()
        if book_id not in self.connections:
            self.connections[book_id] = set()
        self.connections[book_id].add(websocket)
        debug("websocket", "book_id={} WebSocket connected, total connections={}", book_id, len(self.connections[book_id]))

    def disconnect(self, book_id: str, websocket: WebSocket):
        debug("websocket", "book_id={} WebSocket disconnecting", book_id)
        if book_id in self.connections:
            self.connections[book_id].discard(websocket)
            if not self.connections[book_id]:
                del self.connections[book_id]
                debug("websocket", "book_id={} All connections closed, removed from tracker", book_id)

    async def send_progress(self, book_id: str, progress: int, message: str, status: str = "processing", type: str = "analyze"):
        """Send progress update to all clients watching this book.

        Args:
            book_id: 书籍 ID
            progress: 进度 0-100
            message: 状态描述
            status: processing | completed | failed
            type: analyze | manuscript
        """
        debug("websocket", "book_id={} send_progress progress={} message={} status={} type={}", book_id, progress, message, status, type)
        if book_id not in self.connections:
            debug("websocket", "book_id={} No connections found, skipping send", book_id)
            return

        # Validate and serialize via schema
        progress_msg = ProgressMessage(
            progress=progress,
            message=message,
            status=ProgressStatus(status),
            type=ProgressType(type)
        )
        payload = progress_msg.model_dump_json()
        debug("websocket", "book_id={} payload={}", book_id, payload)
        disconnected = set()
        for websocket in self.connections[book_id]:
            try:
                await websocket.send_text(payload)
                debug("websocket", "book_id={} Sent to client successfully", book_id)
            except Exception as e:
                debug("websocket", "book_id={} Send failed error={}", book_id, str(e))
                disconnected.add(websocket)
        for ws in disconnected:
            self.connections[book_id].discard(ws)


# Singleton instance
manager = ConnectionManager()
