"""Integration tests for reference sets API."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_reference_set_and_entries(admin_client: AsyncClient):
    create = await admin_client.post(
        "/api/v1/reference-sets",
        json={"name": "test_bad_ips", "set_type": "ip", "description": "test"},
    )
    assert create.status_code == 201
    set_id = create.json()["id"]

    add = await admin_client.post(
        f"/api/v1/reference-sets/{set_id}/entries",
        json={"values": ["10.0.0.99", "10.0.0.100"]},
    )
    assert add.status_code == 200
    assert len(add.json()) == 2

    lookup = await admin_client.get("/api/v1/reference-sets/lookup", params={"value": "10.0.0.99", "set_type": "ip"})
    assert lookup.status_code == 200
    assert len(lookup.json()["matches"]) >= 1


@pytest.mark.asyncio
async def test_siem_ref_filter(admin_client: AsyncClient):
    create = await admin_client.post(
        "/api/v1/reference-sets",
        json={"name": "siem_ref_ips", "set_type": "ip"},
    )
    set_id = create.json()["id"]
    await admin_client.post(
        f"/api/v1/reference-sets/{set_id}/entries",
        json={"values": ["203.0.113.77"]},
    )

    res = await admin_client.get("/api/v1/search/siem", params={"q": "source_ip:ref:siem_ref_ips"})
    assert res.status_code == 200
    assert res.json()["parsed"]["in_filters"]["source_ip"] == ["203.0.113.77"]


@pytest.mark.asyncio
async def test_reference_set_triggers_detection_alert(analyst_client: AsyncClient):
    from tests.integration.helpers import enroll_test_host, ingest_events

    host_id, api_key = await enroll_test_host(analyst_client, "ref-intel-detect-host")

    create = await analyst_client.post(
        "/api/v1/reference-sets",
        json={"name": "detect_bad_ips", "set_type": "ip"},
    )
    assert create.status_code == 201
    set_id = create.json()["id"]
    await analyst_client.post(
        f"/api/v1/reference-sets/{set_id}/entries",
        json={"values": ["198.51.100.42"]},
    )

    await ingest_events(
        analyst_client,
        api_key,
        [{
            "event_type": "ssh_login_failure",
            "severity": "medium",
            "description": "Failed login from bad IP",
            "source": "test",
            "raw_log": "failed login",
            "timestamp": "2026-07-07T12:00:00+00:00",
            "metadata": {"source_ip": "198.51.100.42"},
        }],
    )

    alerts = await analyst_client.get("/api/v1/alerts", params={"host_id": host_id, "status": "open"})
    assert alerts.status_code == 200
    titles = [a["title"] for a in alerts.json()["items"]]
    assert any("Threat Intel Match" in t for t in titles)
