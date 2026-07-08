"""Integration tests for read replica admin endpoints."""

import pytest


@pytest.mark.asyncio
async def test_system_replicas_primary_only(admin_client):
    res = await admin_client.get("/api/v1/system/replicas")
    assert res.status_code == 200
    body = res.json()
    assert body["enabled"] is False
    assert body["routing"] == "primary_only"
    assert body["read_url_configured"] is False
    assert "GET /api/v1/search" in body["routed_endpoints"]


@pytest.mark.asyncio
async def test_system_pool_includes_read_role(admin_client):
    res = await admin_client.get("/api/v1/system/pool")
    assert res.status_code == 200
    body = res.json()
    assert "primary" in body
    assert "read" in body
    assert body["read"]["configured"] is False
    assert body["primary"]["configured"] is True
