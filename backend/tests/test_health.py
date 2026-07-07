"""Health probe endpoint tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_liveness_always_200():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for path in ("/health", "/health/live"):
            res = await client.get(path)
            assert res.status_code == 200
            assert res.json()["status"] == "alive"


@pytest.mark.asyncio
async def test_readiness_returns_status_code():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/health/ready")
        assert res.status_code in (200, 503)
        body = res.json()
        assert body["status"] in ("ready", "degraded")
        assert "checks" in body


@pytest.mark.asyncio
async def test_startup_returns_status_code():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/health/startup")
        assert res.status_code in (200, 503)
        body = res.json()
        assert body["status"] in ("started", "starting")
        assert "database" in body["checks"]
