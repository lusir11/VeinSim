"""Redis-based progress publisher for Celery tasks.

The Celery worker publishes progress events to Redis pub/sub channels.
A separate async task in the FastAPI process subscribes and forwards
to WebSocket clients via ws_manager.
"""

import json
import logging
import time
from typing import Any

import redis

from app.config import settings

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None
CHANNEL_PREFIX = "sim_progress:"


def _get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


def publish_progress(simulation_id: str, event_type: str, data: dict[str, Any]) -> None:
    """Publish a progress event to Redis pub/sub.

    Called from Celery worker (synchronous context).
    """
    channel = f"{CHANNEL_PREFIX}{simulation_id}"
    message = {
        "type": event_type,
        "simulation_id": simulation_id,
        "timestamp": time.time(),
        **data,
    }
    try:
        _get_redis().publish(channel, json.dumps(message))
    except Exception as exc:
        logger.warning("Failed to publish progress: %s", exc)


def publish_status(simulation_id: str, status: str, **extra: Any) -> None:
    """Shortcut for status change events."""
    publish_progress(simulation_id, "status", {"status": status, **extra})


def publish_iteration(simulation_id: str, iteration: int, residual: float, **extra: Any) -> None:
    """Shortcut for iteration progress events."""
    publish_progress(simulation_id, "progress", {
        "iteration": iteration,
        "residual": residual,
        **extra,
    })


def publish_result(simulation_id: str, metrics: dict, file_keys: dict | None = None) -> None:
    """Shortcut for final result events."""
    publish_progress(simulation_id, "result", {
        "metrics": metrics,
        "file_keys": file_keys or {},
    })
