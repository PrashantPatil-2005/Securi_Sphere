"""Integration tests for system admin endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_system_health_admin_only(analyst_client: AsyncClient, admin_client: AsyncClient):
    denied = await analyst_client.get("/api/v1/system/health")
    assert denied.status_code == 403

    health = await admin_client.get("/api/v1/system/health")
    assert health.status_code == 200
    body = health.json()
    assert "status" in body
    assert "search_backend" in body
    assert "job_queue_backend" in body


@pytest.mark.asyncio
async def test_pipeline_map(admin_client: AsyncClient):
    res = await admin_client.get("/api/v1/system/pipeline")
    assert res.status_code == 200
    body = res.json()
    assert body["model"] == "ibm_qradar_3_layer"
    assert len(body["layers"]) >= 3
