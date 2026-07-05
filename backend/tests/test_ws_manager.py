"""Unit tests for WebSocket connection manager."""

import pytest

from app.websocket.manager import ConnectionManager


@pytest.mark.asyncio
async def test_memory_broadcast_no_connections():
    mgr = ConnectionManager()
    await mgr._broadcast_local({"type": "test", "data": {}})
    assert mgr.active == []


def test_default_backend_is_memory():
    mgr = ConnectionManager()
    assert mgr.backend_name == "memory"
