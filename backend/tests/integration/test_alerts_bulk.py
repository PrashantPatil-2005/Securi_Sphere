"""HTTP integration tests for bulk alert actions."""

import pytest
from httpx import AsyncClient

from tests.integration.helpers import enroll_test_host, event_payload, ingest_events


async def _open_alerts(client: AsyncClient, host_id: str, min_count: int = 1) -> list[dict]:
    res = await client.get("/api/v1/alerts", params={"host_id": host_id, "status": "open"})
    assert res.status_code == 200, res.text
    items = res.json()["items"]
    if len(items) < min_count:
        pytest.skip(f"Expected at least {min_count} open alerts, found {len(items)}")
    return items


@pytest.mark.asyncio
async def test_viewer_cannot_bulk_update_alerts(viewer_client: AsyncClient):
    res = await viewer_client.patch(
        "/api/v1/alerts/bulk",
        json={"alert_ids": ["00000000-0000-0000-0000-000000000099"], "status": "resolved"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_bulk_resolve_and_assign(analyst_client: AsyncClient):
    host_id, api_key = await enroll_test_host(analyst_client, "bulk-alert-host")

    await ingest_events(
        analyst_client,
        api_key,
        [event_payload("ssh_login_failure", severity="medium") for _ in range(6)],
    )

    alerts = await _open_alerts(analyst_client, host_id)
    alert_ids = [a["id"] for a in alerts[:2]]
    assert len(alert_ids) >= 1

    me = await analyst_client.get("/api/v1/auth/me")
    assert me.status_code == 200
    analyst_id = me.json()["id"]

    assign = await analyst_client.patch(
        "/api/v1/alerts/bulk",
        json={"alert_ids": alert_ids, "assigned_to": analyst_id, "status": "investigating"},
    )
    assert assign.status_code == 200, assign.text
    assign_body = assign.json()
    assert assign_body["updated"] == len(alert_ids)
    assert assign_body["not_found"] == []

    listed = await analyst_client.get("/api/v1/alerts", params={"host_id": host_id, "status": "investigating"})
    assert listed.status_code == 200
    investigating = {a["id"]: a for a in listed.json()["items"]}
    for aid in alert_ids:
        assert investigating[aid]["status"] == "investigating"
        assert investigating[aid]["assigned_to"] == analyst_id

    resolve = await analyst_client.patch(
        "/api/v1/alerts/bulk",
        json={"alert_ids": alert_ids, "status": "resolved"},
    )
    assert resolve.status_code == 200, resolve.text
    assert resolve.json()["updated"] == len(alert_ids)

    resolved = await analyst_client.get("/api/v1/alerts", params={"host_id": host_id, "status": "resolved"})
    assert resolved.status_code == 200
    resolved_ids = {a["id"] for a in resolved.json()["items"]}
    assert all(aid in resolved_ids for aid in alert_ids)


@pytest.mark.asyncio
async def test_bulk_update_reports_not_found(analyst_client: AsyncClient):
    missing = "00000000-0000-0000-0000-000000000099"
    res = await analyst_client.patch(
        "/api/v1/alerts/bulk",
        json={"alert_ids": [missing], "status": "resolved"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["updated"] == 0
    assert body["not_found"] == [missing]
