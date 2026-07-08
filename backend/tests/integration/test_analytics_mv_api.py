"""Integration tests for analytics materialized view admin endpoints."""

import pytest


@pytest.mark.asyncio
async def test_analytics_mvs_status(admin_client):
    res = await admin_client.get("/api/v1/system/analytics-mvs")
    assert res.status_code == 200
    body = res.json()
    assert body["enabled"] is False  # TESTING disables MV routing
    assert "mv_events_daily" in body["expected"]
    assert isinstance(body["views"], list)


@pytest.mark.asyncio
async def test_analytics_mvs_refresh_disabled_in_testing(admin_client):
    res = await admin_client.post("/api/v1/system/analytics-mvs/refresh")
    assert res.status_code == 400
    body = res.json()
    message = body.get("detail") or body.get("error", {}).get("message", "")
    assert "disabled" in message.lower()
