"""Redis pub/sub transport for cross-process WebSocket broadcasts."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

WS_CHANNEL = "securi:ws:broadcast"

_redis = None
_pool = None


async def get_redis():
    global _redis, _pool
    from app.config import settings

    if not settings.redis_url:
        return None
    if _redis is not None:
        return _redis
    try:
        from redis.asyncio import Redis

        if _pool is None:
            _pool = Redis.from_url(
                settings.redis_url,
                decode_responses=True,
                max_connections=5,
            )
        _redis = _pool
        await _redis.ping()
    except Exception as exc:
        logger.warning("Redis WebSocket pub/sub unavailable: %s", exc)
        _redis = None
        _pool = None
    return _redis


async def close_redis() -> None:
    global _redis, _pool
    if _pool is not None:
        try:
            await _pool.aclose()
        except Exception:
            pass
    _redis = None
    _pool = None


async def publish_ws_message(message: dict[str, Any]) -> bool:
    redis = await get_redis()
    if not redis:
        return False
    try:
        await redis.publish(WS_CHANNEL, json.dumps(message))
        return True
    except Exception:
        logger.debug("Redis publish failed", exc_info=True)
        return False


async def ws_pubsub_ping() -> bool:
    redis = await get_redis()
    if not redis:
        return False
    try:
        await redis.ping()
        return True
    except Exception:
        return False
