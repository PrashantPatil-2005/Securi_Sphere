"""HTTP integration tests for in-app notification history."""

import pytest
from httpx import AsyncClient

from tests.integration.helpers import enroll_test_host, event_payload, ingest_events


@pytest.mark.asyncio
async def test_notification_history_after_alert(analyst_client: AsyncClient):
    _, api_key = await enroll_test_host(analyst_client, "notif-history-host")

    await ingest_events(
        analyst_client,
        api_key,
        [event_payload("ssh_login_failure", severity="medium") for _ in range(6)],
    )

    history = await analyst_client.get("/api/v1/notifications/history")
    assert history.status_code == 200, history.text
    body = history.json()
    assert body["total"] >= 1
    assert body["unread_count"] >= 1
    assert any(n["kind"] == "alert" for n in body["items"])

    notif_id = body["items"][0]["id"]
    mark = await analyst_client.patch(f"/api/v1/notifications/{notif_id}/read")
    assert mark.status_code == 200, mark.text

    unread = await analyst_client.get("/api/v1/notifications/unread-count")
    assert unread.status_code == 200
    assert unread.json()["unread_count"] == body["unread_count"] - 1


@pytest.mark.asyncio
async def test_mark_all_notifications_read(analyst_client: AsyncClient):
    history = await analyst_client.get("/api/v1/notifications/history")
    assert history.status_code == 200
    if history.json()["unread_count"] == 0:
        pytest.skip("No unread notifications to mark")

    res = await analyst_client.post("/api/v1/notifications/read-all")
    assert res.status_code == 200, res.text
    assert res.json()["marked"] >= 1

    unread = await analyst_client.get("/api/v1/notifications/unread-count")
    assert unread.json()["unread_count"] == 0
