"""Integration tests for UEBA API."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ueba_summary(analyst_client: AsyncClient):
    res = await analyst_client.get("/api/v1/ueba/summary")
    assert res.status_code == 200
    body = res.json()
    assert "open_count" in body
    assert body["enabled"] is True


@pytest.mark.asyncio
async def test_ueba_scan_and_list(analyst_client: AsyncClient):
    scan = await analyst_client.post("/api/v1/ueba/scan")
    assert scan.status_code == 200
    assert scan.json()["enabled"] is True

    listed = await analyst_client.get("/api/v1/ueba/anomalies")
    assert listed.status_code == 200
    assert isinstance(listed.json(), list)


@pytest.mark.asyncio
async def test_viewer_cannot_scan(viewer_client: AsyncClient):
    res = await viewer_client.post("/api/v1/ueba/scan")
    assert res.status_code == 403
