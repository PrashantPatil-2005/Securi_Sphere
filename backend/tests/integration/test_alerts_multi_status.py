"""HTTP integration tests for dashboard alerts-list filtering.

The dashboard "Active Threats" card requests alerts with repeated
``status`` params (open + investigating) and a valid enum sort, so the
list endpoint must accept both without a 422.
"""

import uuid

import pytest
from httpx import AsyncClient

from tests.integration.helpers import enroll_test_host, event_payload, ingest_events


async def _make_open_and_investigating(client: AsyncClient) -> tuple[dict, dict]:
    """Enroll a host, generate alerts, and return one open + one investigating."""
    name = f"multi-status-{uuid.uuid4().hex[:8]}"
    host_id, api_key = await enroll_test_host(client, name)

    await ingest_events(
        client,
        api_key,
        [
            event_payload(
                "ssh_login_failure",
                severity="high",
                description=f"multi-status brute force {i}",
                raw_log=f"multi-status brute force attempt {i} from 10.0.0.{i + 1}",
            )
            for i in range(6)
        ],
    )

    listed = await client.get("/api/v1/alerts", params={"host_id": host_id, "status": "open"})
    assert listed.status_code == 200, listed.text
    open_items = listed.json()["items"]
    if len(open_items) < 2:
        pytest.skip("expected at least two open alerts after ingestion")

    open_alert, investigating_alert = open_items[0], open_items[1]
    flip = await client.patch(
        "/api/v1/alerts/bulk",
        json={"alert_ids": [investigating_alert["id"]], "status": "investigating"},
    )
    assert flip.status_code == 200, flip.text
    assert flip.json()["updated"] == 1
    return open_alert, investigating_alert


@pytest.mark.asyncio
async def test_alerts_list_accepts_repeated_status_params(analyst_client: AsyncClient):
    open_alert, investigating_alert = await _make_open_and_investigating(analyst_client)

    res = await analyst_client.get(
        "/api/v1/alerts",
        params=[
            ("host_id", open_alert["host_id"]),
            ("status", "open"),
            ("status", "investigating"),
            ("sort", "newest"),
        ],
    )
    assert res.status_code == 200, res.text
    by_id = {a["id"]: a for a in res.json()["items"]}
    assert open_alert["id"] in by_id
    assert investigating_alert["id"] in by_id
    assert by_id[open_alert["id"]]["status"] == "open"
    assert by_id[investigating_alert["id"]]["status"] == "investigating"


@pytest.mark.asyncio
async def test_alerts_list_single_status_still_filters(analyst_client: AsyncClient):
    open_alert, investigating_alert = await _make_open_and_investigating(analyst_client)

    res = await analyst_client.get(
        "/api/v1/alerts",
        params={"host_id": open_alert["host_id"], "status": "open", "sort": "newest"},
    )
    assert res.status_code == 200, res.text
    ids = {a["id"] for a in res.json()["items"]}
    assert open_alert["id"] in ids
    assert investigating_alert["id"] not in ids
