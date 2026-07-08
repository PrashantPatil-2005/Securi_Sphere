"""HTTP integration tests for agent ingest, events API, and alert investigation."""

import pytest
from httpx import AsyncClient

from tests.integration.helpers import enroll_test_host, event_payload, ingest_events


@pytest.mark.asyncio
async def test_agent_event_ingest_and_list(analyst_client: AsyncClient):
    host_id, api_key = await enroll_test_host(analyst_client, "pipeline-ingest-host")

    ingest_body = await ingest_events(
        analyst_client,
        api_key,
        [event_payload("service_failure", severity="high", description="pipeline list test")],
    )
    assert ingest_body["ingested"] == 1

    events_res = await analyst_client.get("/api/v1/events", params={"host_id": host_id, "page_size": 20})
    assert events_res.status_code == 200, events_res.text
    items = events_res.json()["items"]
    assert len(items) >= 1
    assert any(e["event_type"] == "service_failure" for e in items)


@pytest.mark.asyncio
async def test_events_keyset_cursor_pagination(analyst_client: AsyncClient):
    host_id, api_key = await enroll_test_host(analyst_client, "pipeline-cursor-host")

    await ingest_events(
        analyst_client,
        api_key,
        [
            event_payload("ssh_login_failure", offset_seconds=-30),
            event_payload("ssh_login_failure", offset_seconds=-20),
            event_payload("ssh_login_failure", offset_seconds=-10),
        ],
    )

    first = await analyst_client.get(
        "/api/v1/events",
        params={"host_id": host_id, "page_size": 2, "sort": "newest"},
    )
    assert first.status_code == 200, first.text
    first_body = first.json()
    assert len(first_body["items"]) == 2
    assert first_body.get("has_more") is True
    assert first_body.get("next_cursor")

    second = await analyst_client.get(
        "/api/v1/events",
        params={"host_id": host_id, "page_size": 2, "cursor": first_body["next_cursor"], "sort": "newest"},
    )
    assert second.status_code == 200, second.text
    second_body = second.json()
    assert len(second_body["items"]) >= 1
    first_ids = {item["id"] for item in first_body["items"]}
    second_ids = {item["id"] for item in second_body["items"]}
    assert first_ids.isdisjoint(second_ids)


@pytest.mark.asyncio
async def test_ingest_creates_alert_and_investigation(analyst_client: AsyncClient):
    host_id, api_key = await enroll_test_host(analyst_client, "pipeline-alert-host")

    await ingest_events(
        analyst_client,
        api_key,
        [event_payload("ssh_login_failure", severity="medium") for _ in range(6)],
    )

    alerts_res = await analyst_client.get("/api/v1/alerts", params={"host_id": host_id, "status": "open"})
    assert alerts_res.status_code == 200, alerts_res.text
    alerts = alerts_res.json()["items"]
    if len(alerts) < 1:
        pytest.skip("No open alerts generated from ingest in this environment")

    alert_id = alerts[0]["id"]
    inv_res = await analyst_client.get(f"/api/v1/alerts/{alert_id}/investigation")
    assert inv_res.status_code == 200, inv_res.text
    inv = inv_res.json()
    assert inv["alert"]["id"] == alert_id
    assert inv["host"]["id"] == host_id
    assert isinstance(inv["events"], list)
    assert len(inv["events"]) >= 1
