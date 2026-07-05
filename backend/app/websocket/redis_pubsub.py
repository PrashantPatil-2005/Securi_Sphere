"""Redis pub/sub transport for cross-process WebSocket broadcasts."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

WS_CHANNEL = "securi:ws:broadcast"

_redis = None


async def get_redis():
    global _redis
    from app.config import settings

    if not settings.redis_url:
        return None
    if _redis is None:
        try:
            from redis.asyncio import Redis

            _redis = Redis.from_url(settings.redis_url, decode_responses=True)
            await _redis.ping()
        except Exception as exc:
            logger.warning("Redis WebSocket pub/sub unavailable: %s", exc)
            _redis = False
    return _redis if _redis is not False else None


async def publish_ws_message(message: dict[str, Any]) -> bool:
    redis = await get_redis()
    if not redis:
        return False
    await redis.publish(WS_CHANNEL, json.dumps(message))
    return True


async def ws_pubsub_ping() -> bool:
    redis = await get_redis()
    if not redis:
        return False
    try:
        await redis.ping()
        return True
    except Exception:
        return False
