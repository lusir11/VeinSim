"""WebSocket endpoint for real-time simulation monitoring."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.ws_manager import ws_manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/simulations/{simulation_id}")
async def simulation_ws(websocket: WebSocket, simulation_id: str):
    """
    WebSocket connection for watching a specific simulation.

    Client receives:
    - {"type": "status", "status": "meshing"|"running"|"converged"|"failed", ...}
    - {"type": "progress", "iteration": 42, "residual": 1.2e-4, "timestamp": ...}
    - {"type": "result", "metrics": {...}, "file_keys": {...}}
    - {"type": "error", "message": "..."}
    """
    await ws_manager.connect(websocket, simulation_id)
    try:
        while True:
            # Keep connection alive; client can send heartbeat or commands
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, simulation_id)
    except Exception:
        ws_manager.disconnect(websocket, simulation_id)
