"""WebSocket manager for real-time simulation progress updates."""

import json
import logging
from collections import defaultdict
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections grouped by simulation_id."""

    def __init__(self) -> None:
        # simulation_id -> list of active WebSocket connections
        self._connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, simulation_id: str) -> None:
        await websocket.accept()
        self._connections[simulation_id].append(websocket)
        logger.info("WS connected: sim=%s (total=%d)", simulation_id, len(self._connections[simulation_id]))

    def disconnect(self, websocket: WebSocket, simulation_id: str) -> None:
        conns = self._connections[simulation_id]
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            del self._connections[simulation_id]
        logger.info("WS disconnected: sim=%s", simulation_id)

    async def broadcast(self, simulation_id: str, message: dict[str, Any]) -> None:
        """Send a JSON message to all connections watching a simulation."""
        dead: list[WebSocket] = []
        payload = json.dumps(message)
        for ws in self._connections.get(simulation_id, []):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections[simulation_id].remove(ws)

    async def send_global(self, message: dict[str, Any]) -> None:
        """Broadcast to ALL connected clients (e.g. dashboard stats update)."""
        payload = json.dumps(message)
        for sim_conns in self._connections.values():
            for ws in sim_conns:
                try:
                    await ws.send_text(payload)
                except Exception:
                    pass


# Singleton
ws_manager = ConnectionManager()
