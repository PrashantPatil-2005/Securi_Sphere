"""Integration tests for timeline HTTP API."""

import pytest
from httpx import AsyncClient

from tests.integration.helpers import enroll_test_host


@pytest.mark.asyncio
async def test_list_timelines_after_simulation(analyst_client: AsyncClient):
    host_id, _ = await enroll_test_host(analyst_client, "timeline-api-host")

    sim = await analyst_client.post(f"/api/v1/simulation/run/brute_force?host_id={host_id}")
    if sim.status_code == 403:
        pytest.skip("Simulation disabled")
    assert sim.status_code == 200

    timelines = await analyst_client.get("/api/v1/timelines", params={"host_id": host_id})
    assert timelines.status_code == 200
    items = timelines.json()
    assert isinstance(items, list)

    if items:
        events = await analyst_client.get(f"/api/v1/timelines/{items[0]['id']}/events")
        assert events.status_code == 200
        assert isinstance(events.json(), list)
