import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

from app.config import settings

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket connections with optional Redis pub/sub for multi-instance broadcast."""

    def __init__(self) -> None:
        self.active: list[WebSocket] = []
        self._listener_task: asyncio.Task | None = None
        self.backend_name = "memory"
        self._use_redis = (
            settings.ws_pubsub_backend == "redis" and bool(settings.redis_url)
        )
        if settings.ws_pubsub_backend == "redis" and not settings.redis_url:
            logger.warning("WS_PUBSUB_BACKEND=redis but REDIS_URL is unset; using in-process broadcast")
        elif self._use_redis:
            self.backend_name = "redis"

    async def start(self) -> None:
        if not self._use_redis or settings.testing:
            return
        if self._listener_task is None:
            self._listener_task = asyncio.create_task(self._redis_listener())
            logger.info("WebSocket Redis pub/sub listener started")

    async def stop(self) -> None:
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active:
            self.active.remove(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        if self._use_redis:
            from app.websocket.redis_pubsub import publish_ws_message

            published = await publish_ws_message(message)
            if not published:
                await self._broadcast_local(message)
            return
        await self._broadcast_local(message)

    async def _broadcast_local(self, message: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        payload = json.dumps(message)
        for ws in self.active:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def _redis_listener(self) -> None:
        from app.websocket.redis_pubsub import WS_CHANNEL, get_redis

        redis = await get_redis()
        if not redis:
            return
        pubsub = redis.pubsub()
        await pubsub.subscribe(WS_CHANNEL)
        try:
            async for raw in pubsub.listen():
                if raw.get("type") != "message":
                    continue
                try:
                    message = json.loads(raw["data"])
                except (json.JSONDecodeError, TypeError):
                    logger.warning("invalid WebSocket pub/sub payload")
                    continue
                await self._broadcast_local(message)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("WebSocket Redis listener failed")
        finally:
            await pubsub.unsubscribe(WS_CHANNEL)
            await pubsub.close()


ws_manager = ConnectionManager()
