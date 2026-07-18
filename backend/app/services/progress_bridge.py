"""Background task: subscribes to Redis pub/sub and forwards events to WebSocket clients."""

import asyncio
import json
import logging

import redis.asyncio as aioredis

from app.config import settings
from app.services.ws_manager import ws_manager

logger = logging.getLogger(__name__)

CHANNEL_PREFIX = "sim_progress:"
_redis_pubsub: aioredis.client.PubSub | None = None


async def start_progress_bridge() -> None:
    """Start the Redis pub/sub -> WebSocket bridge as a background task."""
    global _redis_pubsub

    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    _redis_pubsub = r.pubsub()

    # Subscribe to all simulation progress channels using pattern
    await _redis_pubsub.psubscribe(f"{CHANNEL_PREFIX}*")
    logger.info("Progress bridge started, listening on %s*", CHANNEL_PREFIX)

    asyncio.create_task(_listen_loop())


async def _listen_loop() -> None:
    """Main loop: read Redis messages and forward to WebSocket clients."""
    assert _redis_pubsub is not None
    try:
        async for message in _redis_pubsub.listen():
            if message["type"] != "pmessage":
                continue
            try:
                channel: str = message["channel"]
                if isinstance(channel, bytes):
                    channel = channel.decode()
                # Extract simulation_id from channel name
                simulation_id = channel.replace(CHANNEL_PREFIX, "")
                data = json.loads(message["data"])
                await ws_manager.broadcast(simulation_id, data)
            except Exception as exc:
                logger.warning("Failed to forward WS message: %s", exc)
    except asyncio.CancelledError:
        logger.info("Progress bridge cancelled")
    except Exception as exc:
        logger.error("Progress bridge error: %s", exc)


async def stop_progress_bridge() -> None:
    """Clean shutdown of the pub/sub listener."""
    global _redis_pubsub
    if _redis_pubsub:
        await _redis_pubsub.punsubscribe()
        await _redis_pubsub.close()
        _redis_pubsub = None
