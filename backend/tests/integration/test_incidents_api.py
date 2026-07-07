"""Integration tests for incidents CRUD."""

import pytest
from httpx import AsyncClient

from tests.integration.helpers import enroll_test_host, event_payload, ingest_events


@pytest.mark.asyncio
async def test_incident_crud_and_notes(analyst_client: AsyncClient):
    host_id, api_key = await enroll_test_host(analyst_client, "incident-crud-host")
    await ingest_events(
        analyst_client,
        api_key,
        [event_payload("service_failure", severity="high")],
    )

    alerts = await analyst_client.get("/api/v1/alerts", params={"host_id": host_id, "status": "open"})
    assert alerts.status_code == 200
    alert_items = alerts.json()["items"]
    assert alert_items

    create = await analyst_client.post(
        "/api/v1/incidents",
        json={"title": "Test incident", "description": "Integration test", "severity": "high", "host_id": host_id},
    )
    assert create.status_code == 200
    incident_id = create.json()["id"]

    link = await analyst_client.post(f"/api/v1/incidents/{incident_id}/alerts/{alert_items[0]['id']}")
    assert link.status_code == 200

    note = await analyst_client.post(
        f"/api/v1/incidents/{incident_id}/notes",
        json={"content": "Investigation started"},
    )
    assert note.status_code == 200

    detail = await analyst_client.get(f"/api/v1/incidents/{incident_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["title"] == "Test incident"
    assert len(body["notes"]) == 1
    assert alert_items[0]["id"] in body["alert_ids"]

    listing = await analyst_client.get("/api/v1/incidents")
    assert listing.status_code == 200
    assert any(i["id"] == incident_id for i in listing.json())
