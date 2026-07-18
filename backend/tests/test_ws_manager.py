"""Unit tests for WebSocket connection manager.

Tests connection lifecycle, broadcast, dead connection cleanup,
and Redis pub/sub integration path.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.websocket.manager import ConnectionManager


def _mock_ws():
    """Create a mock WebSocket."""
    ws = AsyncMock()
    ws.send_text = AsyncMock()
    ws.close = AsyncMock()
    return ws


class TestConnectionManagerInit:
    def test_default_backend_is_memory(self):
        mgr = ConnectionManager()
        assert mgr.backend_name == "memory"
        assert mgr.active == []

    def test_active_starts_empty(self):
        mgr = ConnectionManager()
        assert len(mgr.active) == 0


class TestConnectDisconnect:
    @pytest.mark.asyncio
    async def test_connect_adds_to_active(self):
        mgr = ConnectionManager()
        ws = _mock_ws()
        await mgr.connect(ws)
        assert ws in mgr.active
        assert len(mgr.active) == 1
        ws.accept.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disconnect_removes_from_active(self):
        mgr = ConnectionManager()
        ws = _mock_ws()
        await mgr.connect(ws)
        mgr.disconnect(ws)
        assert ws not in mgr.active

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_is_noop(self):
        mgr = ConnectionManager()
        ws = _mock_ws()
        mgr.disconnect(ws)  # Should not raise
        assert mgr.active == []

    @pytest.mark.asyncio
    async def test_multiple_connections(self):
        mgr = ConnectionManager()
        ws1, ws2, ws3 = _mock_ws(), _mock_ws(), _mock_ws()
        await mgr.connect(ws1)
        await mgr.connect(ws2)
        await mgr.connect(ws3)
        assert len(mgr.active) == 3
        mgr.disconnect(ws2)
        assert len(mgr.active) == 2
        assert ws1 in mgr.active
        assert ws3 in mgr.active


class TestBroadcastLocal:
    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all(self):
        mgr = ConnectionManager()
        ws1, ws2 = _mock_ws(), _mock_ws()
        await mgr.connect(ws1)
        await mgr.connect(ws2)
        msg = {"type": "test", "data": {"key": "value"}}
        await mgr._broadcast_local(msg)
        payload = json.dumps(msg)
        ws1.send_text.assert_awaited_once_with(payload)
        ws2.send_text.assert_awaited_once_with(payload)

    @pytest.mark.asyncio
    async def test_broadcast_empty_list(self):
        mgr = ConnectionManager()
        await mgr._broadcast_local({"type": "test"})
        # No error, no calls

    @pytest.mark.asyncio
    async def test_dead_connection_removed(self):
        mgr = ConnectionManager()
        ws_good = _mock_ws()
        ws_bad = _mock_ws()
        ws_bad.send_text.side_effect = ConnectionError("broken pipe")
        await mgr.connect(ws_good)
        await mgr.connect(ws_bad)
        await mgr._broadcast_local({"type": "test"})
        assert ws_bad not in mgr.active
        assert ws_good in mgr.active

    @pytest.mark.asyncio
    async def test_all_dead_connections_removed(self):
        mgr = ConnectionManager()
        ws1 = _mock_ws()
        ws2 = _mock_ws()
        ws1.send_text.side_effect = ConnectionError("pipe1")
        ws2.send_text.side_effect = ConnectionError("pipe2")
        await mgr.connect(ws1)
        await mgr.connect(ws2)
        await mgr._broadcast_local({"type": "test"})
        assert mgr.active == []


class TestStop:
    @pytest.mark.asyncio
    async def test_stop_closes_all_connections(self):
        mgr = ConnectionManager()
        ws1, ws2 = _mock_ws(), _mock_ws()
        await mgr.connect(ws1)
        await mgr.connect(ws2)
        await mgr.stop()
        ws1.close.assert_awaited_once()
        ws2.close.assert_awaited_once()
        assert mgr.active == []

    @pytest.mark.asyncio
    async def test_stop_handles_already_closed(self):
        mgr = ConnectionManager()
        ws = _mock_ws()
        ws.close.side_effect = Exception("already closed")
        await mgr.connect(ws)
        await mgr.stop()  # Should not raise
        assert mgr.active == []

    @pytest.mark.asyncio
    async def test_stop_no_connections(self):
        mgr = ConnectionManager()
        await mgr.stop()  # Should not raise

    @pytest.mark.asyncio
    async def test_stop_cancels_listener(self):
        mgr = ConnectionManager()
        # Create a real task that sleeps forever, then cancel it
        async def _sleep_forever():
            try:
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                raise

        task = asyncio.create_task(_sleep_forever())
        mgr._listener_task = task
        await mgr.stop()
        assert task.cancelled()
        assert mgr._listener_task is None


class TestBroadcastMemory:
    @pytest.mark.asyncio
    async def test_broadcast_memory_calls_local(self):
        mgr = ConnectionManager()
        ws = _mock_ws()
        await mgr.connect(ws)
        msg = {"type": "alert", "data": {"id": 1}}
        with patch.object(mgr, "_broadcast_local", new_callable=AsyncMock) as mock_local:
            await mgr.broadcast(msg)
            mock_local.assert_awaited_once_with(msg)

    @pytest.mark.asyncio
    async def test_broadcast_memory_fallback_on_redis_failure(self):
        """When Redis publish fails, broadcast falls back to local."""
        mgr = ConnectionManager()
        mgr._use_redis = True
        ws = _mock_ws()
        await mgr.connect(ws)
        msg = {"type": "alert"}
        with (
            patch("app.websocket.redis_pubsub.publish_ws_message", new_callable=AsyncMock, return_value=False),
            patch.object(mgr, "_broadcast_local", new_callable=AsyncMock) as mock_local,
        ):
            await mgr.broadcast(msg)
            mock_local.assert_awaited_once_with(msg)

    @pytest.mark.asyncio
    async def test_broadcast_redis_publishes(self):
        """When Redis is available, broadcast publishes via Redis."""
        mgr = ConnectionManager()
        mgr._use_redis = True
        msg = {"type": "alert"}
        with (
            patch("app.websocket.redis_pubsub.publish_ws_message", new_callable=AsyncMock, return_value=True) as mock_pub,
            patch.object(mgr, "_broadcast_local", new_callable=AsyncMock) as mock_local,
        ):
            await mgr.broadcast(msg)
            mock_pub.assert_awaited_once_with(msg)
            mock_local.assert_not_awaited()
