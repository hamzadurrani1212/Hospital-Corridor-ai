# app/broadcast.py
import asyncio
from typing import Set
from fastapi import WebSocket
class Broadcaster:
    def __init__(self):
        # using a set prevents duplicate connections and is faster
        self._clients: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        """Accept and store a new websocket connection."""
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)

    async def disconnect(self, websocket: WebSocket):
        """Safely remove a websocket if it exists."""
        async with self._lock:
            if websocket in self._clients:
                self._clients.remove(websocket)

    async def broadcast_json(self, message: dict):
        """
        Broadcast a JSON message to all connected clients (concurrent).
        Faster than sending one-by-one.
        """
        async with self._lock:
            clients = list(self._clients)  # copy to avoid mutation during iteration

        if not clients:
            return

        tasks = [self._safe_send(ws, message) for ws in clients]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_send(self, ws: WebSocket, message: dict):
        """Send JSON safely; disconnect if the socket is broken."""
        try:
            await ws.send_json(message)
        except Exception:
            try:
                await self.disconnect(ws)
            except Exception:
                pass


# Global singleton instance
broadcaster = Broadcaster()
