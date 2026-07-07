"""Integration tests for analytics summary and retention APIs."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_analytics_summary(analyst_client: AsyncClient):
    res = await analyst_client.get("/api/v1/analytics/summary")
    assert res.status_code == 200
    body = res.json()
    assert "events_today" in body
    assert "alerts_this_month" in body


@pytest.mark.asyncio
async def test_analytics_retention_daily(analyst_client: AsyncClient):
    res = await analyst_client.get("/api/v1/analytics/retention", params={"view": "daily"})
    assert res.status_code == 200
    body = res.json()
    assert body["view"] == "daily"
    assert "events" in body and "alerts" in body
