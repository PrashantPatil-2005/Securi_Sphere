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


@pytest.mark.asyncio
async def test_opensearch_backfill_requires_opensearch_url(admin_client: AsyncClient):
    res = await admin_client.post("/api/v1/system/opensearch/backfill")
    assert res.status_code == 400
    body = res.json()
    message = body.get("detail") or body.get("error", {}).get("message", "")
    assert "opensearch_url" in message.lower()


@pytest.mark.asyncio
async def test_opensearch_backfill_success(monkeypatch, admin_client: AsyncClient):
    import app.routers.system as system_router

    async def fake_backfill(event_limit: int, alert_limit: int):
        return {"events": event_limit, "alerts": alert_limit, "hosts": 7}

    monkeypatch.setattr(system_router.settings, "opensearch_url", "http://opensearch.local:9200")
    monkeypatch.setattr("app.services.opensearch_backfill.run_opensearch_backfill", fake_backfill)

    res = await admin_client.post("/api/v1/system/opensearch/backfill?event_limit=123&alert_limit=11")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["search_backend"] == "opensearch"
    assert body["indexed"] == {"events": 123, "alerts": 11, "hosts": 7}


@pytest.mark.asyncio
async def test_system_health_reports_opensearch_when_enabled(monkeypatch, admin_client: AsyncClient):
    import app.routers.system as system_router

    async def fake_cluster_health():
        return {"status": "green", "number_of_nodes": 1, "indices": 3}

    monkeypatch.setattr(system_router.settings, "opensearch_url", "http://opensearch.local:9200")
    monkeypatch.setattr(system_router.settings, "search_backend", "opensearch")
    monkeypatch.setattr(system_router, "opensearch_enabled", lambda: True)
    monkeypatch.setattr(system_router, "opensearch_cluster_health", fake_cluster_health)

    res = await admin_client.get("/api/v1/system/health")
    assert res.status_code == 200
    body = res.json()
    assert body["search_backend"] == "opensearch"
    assert body["opensearch"]["status"] == "green"
