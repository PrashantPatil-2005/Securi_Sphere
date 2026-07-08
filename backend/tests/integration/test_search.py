"""HTTP integration tests for search endpoints."""

import pytest
from httpx import AsyncClient

from tests.integration.helpers import enroll_test_host, event_payload, ingest_events


@pytest.mark.asyncio
async def test_global_search_finds_host(analyst_client: AsyncClient):
    unique = "globalsearch-host-xy"
    host_id, api_key = await enroll_test_host(analyst_client, unique)

    res = await analyst_client.get("/api/v1/search", params={"q": unique, "exact": "true"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["backend"] == "postgres"
    assert any(h["id"] == host_id for h in body["hosts"])


@pytest.mark.asyncio
async def test_siem_search_finds_ingested_event(analyst_client: AsyncClient):
    unique_type = "ssh_login_failure_integration"
    _, api_key = await enroll_test_host(analyst_client, "siem-search-host")

    await ingest_events(
        analyst_client,
        api_key,
        [event_payload(unique_type, description="integration siem search marker")],
    )

    res = await analyst_client.get(
        "/api/v1/search/siem",
        params={"q": f"event_type:{unique_type}"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["backend"] == "postgres"
    assert body["total_events"] >= 1
    assert any(e["event_type"] == unique_type for e in body["events"])


@pytest.mark.asyncio
async def test_global_search_requires_auth(client: AsyncClient):
    res = await client.get("/api/v1/search", params={"q": "test"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_global_search_falls_back_when_opensearch_unavailable(
    monkeypatch: pytest.MonkeyPatch, analyst_client: AsyncClient
):
    unique = "fallback-global-host-01"
    host_id, _ = await enroll_test_host(analyst_client, unique)

    async def fake_opensearch(*_args, **_kwargs):
        return None

    monkeypatch.setattr("app.search.opensearch_client.global_search_opensearch", fake_opensearch)

    res = await analyst_client.get("/api/v1/search", params={"q": unique})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["backend"] == "postgres"
    assert any(h["id"] == host_id for h in body["hosts"])


@pytest.mark.asyncio
async def test_siem_search_falls_back_when_opensearch_unavailable(
    monkeypatch: pytest.MonkeyPatch, analyst_client: AsyncClient
):
    unique_type = "ssh_login_failure_fallback"
    _, api_key = await enroll_test_host(analyst_client, "siem-fallback-host")
    await ingest_events(
        analyst_client,
        api_key,
        [event_payload(unique_type, description="siem fallback marker")],
    )

    async def fake_opensearch(*_args, **_kwargs):
        return None

    monkeypatch.setattr("app.search.opensearch_client.siem_search_opensearch", fake_opensearch)

    res = await analyst_client.get("/api/v1/search/siem", params={"q": f"event_type:{unique_type}"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["backend"] == "postgres"
    assert any(e["event_type"] == unique_type for e in body["events"])
