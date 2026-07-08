"""Telemetry endpoint tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_telemetry_ingest_and_summary(analyst_client: AsyncClient):
    res = await analyst_client.post(
        "/api/v1/telemetry/events",
        json={
            "event": "simulation_started",
            "properties": {"scenario_id": "multi_stage_attack"},
            "session_id": "test-session",
            "page_path": "/simulation",
        },
    )
    assert res.status_code == 204

    summary = await analyst_client.get("/api/v1/telemetry/summary?days=1")
    assert summary.status_code == 200
    body = summary.json()
    assert body["enabled"] is True
    assert "simulation_started" in body["funnel"] or any(
        e["event"] == "simulation_started" for e in body["events"]
    )


@pytest.mark.asyncio
async def test_telemetry_rejects_unknown_event(analyst_client: AsyncClient):
    res = await analyst_client.post(
        "/api/v1/telemetry/events",
        json={"event": "not_a_real_event"},
    )
    assert res.status_code == 204

    summary = await analyst_client.get("/api/v1/telemetry/summary?days=1")
    events = [e["event"] for e in summary.json()["events"]]
    assert "not_a_real_event" not in events
