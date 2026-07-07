"""Request timeout middleware and resolver tests."""

import asyncio

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.http_timeouts import outbound_timeout, resolve_request_timeout
from app.middleware.request_timeout import RequestTimeoutMiddleware


def test_resolve_request_timeout_paths(monkeypatch):
    monkeypatch.setattr("app.core.http_timeouts.settings.request_timeout_seconds", 60.0)
    monkeypatch.setattr("app.core.http_timeouts.settings.request_timeout_agent_seconds", 120.0)
    monkeypatch.setattr("app.core.http_timeouts.settings.request_timeout_export_seconds", 300.0)

    assert resolve_request_timeout("/health/ready") is None
    assert resolve_request_timeout("/api/v1/alerts") == 60.0
    assert resolve_request_timeout("/api/v1/agent/events") == 120.0
    assert resolve_request_timeout("/api/v1/events/export") == 300.0


def test_outbound_timeout_profiles(monkeypatch):
    monkeypatch.setattr("app.core.http_timeouts.settings.outbound_http_timeout_seconds", 30.0)
    monkeypatch.setattr("app.core.http_timeouts.settings.outbound_http_timeout_short_seconds", 15.0)

    assert outbound_timeout() == 30.0
    assert outbound_timeout(short=True) == 15.0


@pytest.mark.asyncio
async def test_middleware_returns_504_on_slow_request(monkeypatch):
    monkeypatch.setattr("app.middleware.request_timeout.settings.request_timeout_enabled", True)
    monkeypatch.setattr("app.middleware.request_timeout.settings.request_timeout_seconds", 0.05)

    app = FastAPI()
    app.add_middleware(RequestTimeoutMiddleware)

    @app.get("/slow")
    async def slow():
        await asyncio.sleep(0.2)
        return {"ok": True}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/slow")

    assert res.status_code == 504
    assert res.json()["error"]["code"] == "request_timeout"


@pytest.mark.asyncio
async def test_middleware_exempts_health(monkeypatch):
    monkeypatch.setattr("app.middleware.request_timeout.settings.request_timeout_enabled", True)
    monkeypatch.setattr("app.middleware.request_timeout.settings.request_timeout_seconds", 0.05)

    app = FastAPI()
    app.add_middleware(RequestTimeoutMiddleware)

    @app.get("/health/ready")
    async def ready():
        await asyncio.sleep(0.2)
        return {"status": "ready"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/health/ready")

    assert res.status_code == 200
