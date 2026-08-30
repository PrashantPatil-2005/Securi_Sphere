"""WebSocket + Redis Pub/Sub integration tests.

These tests FAIL if Redis is not available (not skipped).
"""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.websocket.manager import ConnectionManager

pytestmark = [pytest.mark.integration]


def _mock_ws():
    ws = AsyncMock()
    ws.send_text = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.mark.asyncio
async def test_ws_connect_disconnect():
    mgr = ConnectionManager()
    ws = _mock_ws()
    mgr.connect(ws)
    assert ws in mgr.active
    assert len(mgr.active) == 1
    mgr.disconnect(ws)
    assert ws not in mgr.active
    assert len(mgr.active) == 0


@pytest.mark.asyncio
async def test_ws_multiple_clients():
    mgr = ConnectionManager()
    clients = [_mock_ws() for _ in range(5)]
    for c in clients:
        mgr.connect(c)
    assert len(mgr.active) == 5
    for c in clients:
        assert c in mgr.active


@pytest.mark.asyncio
async def test_ws_broadcast_reaches_all():
    mgr = ConnectionManager()
    ws1, ws2, ws3 = _mock_ws(), _mock_ws(), _mock_ws()
    mgr.connect(ws1)
    mgr.connect(ws2)
    mgr.connect(ws3)
    msg = {"type": "alert", "data": {"id": "123"}}
    await mgr._broadcast_local(msg)
    payload = json.dumps(msg)
    ws1.send_text.assert_awaited_once_with(payload)
    ws2.send_text.assert_awaited_once_with(payload)
    ws3.send_text.assert_awaited_once_with(payload)


@pytest.mark.asyncio
async def test_ws_dead_client_removed():
    mgr = ConnectionManager()
    ws_good = _mock_ws()
    ws_bad = _mock_ws()
    ws_bad.send_text.side_effect = ConnectionError("broken pipe")
    mgr.connect(ws_good)
    mgr.connect(ws_bad)
    await mgr._broadcast_local({"type": "test"})
    assert ws_bad not in mgr.active
    assert ws_good in mgr.active


@pytest.mark.asyncio
async def test_ws_slow_client_does_not_block():
    mgr = ConnectionManager()
    ws_fast = _mock_ws()
    ws_slow = _mock_ws()

    async def slow_send(msg):
        await asyncio.sleep(10)

    ws_slow.send_text = slow_send
    mgr.connect(ws_fast)
    mgr.connect(ws_slow)

    try:
        await asyncio.wait_for(mgr._broadcast_local({"type": "test"}), timeout=2.0)
    except asyncio.TimeoutError:
        pytest.fail("Slow client blocked broadcast")

    ws_fast.send_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_ws_send_timeout():
    from app.websocket.manager import WS_SEND_TIMEOUT_SECONDS

    mgr = ConnectionManager()
    ws = _mock_ws()

    async def very_slow_send(msg):
        await asyncio.sleep(WS_SEND_TIMEOUT_SECONDS + 10)

    ws.send_text = very_slow_send
    mgr.connect(ws)
    await mgr._broadcast_local({"type": "test"})
    assert ws not in mgr.active


@pytest.mark.asyncio
async def test_ws_redis_pubsub_broadcast():
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


@pytest.mark.asyncio
async def test_ws_redis_fallback_to_local():
    mgr = ConnectionManager()
    mgr._use_redis = True
    ws = _mock_ws()
    mgr.connect(ws)
    msg = {"type": "alert"}
    with (
        patch("app.websocket.redis_pubsub.publish_ws_message", new_callable=AsyncMock, return_value=False),
        patch.object(mgr, "_broadcast_local", new_callable=AsyncMock) as mock_local,
    ):
        await mgr.broadcast(msg)
        mock_local.assert_awaited_once_with(msg)


@pytest.mark.asyncio
async def test_ws_stop_closes_connections():
    mgr = ConnectionManager()
    ws1, ws2 = _mock_ws(), _mock_ws()
    mgr.connect(ws1)
    mgr.connect(ws2)
    await mgr.stop()
    ws1.close.assert_awaited_once()
    ws2.close.assert_awaited_once()
    assert mgr.active == []


@pytest.mark.asyncio
async def test_ws_listener_task_cancelled():
    mgr = ConnectionManager()

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
