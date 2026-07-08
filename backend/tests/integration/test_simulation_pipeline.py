"""Integration test: simulation → offense → incident promotion."""

from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.database import async_session
from app.models.siem import Offense
from tests.integration.helpers import create_test_host


@pytest.mark.asyncio
async def test_simulation_creates_offense_and_promotes(analyst_client: AsyncClient):
    host_id = await create_test_host("sim-pipeline-host", hostname="sim-pipeline")

    sim = await analyst_client.post(f"/api/v1/simulation/run/brute_force?host_id={host_id}")
    if sim.status_code == 403:
        pytest.skip("Simulation requires admin role in this environment")
    assert sim.status_code == 200, sim.text

    offenses_res = await analyst_client.get("/api/v1/offenses")
    assert offenses_res.status_code == 200
    items = offenses_res.json().get("items", [])
    host_offenses = [o for o in items if str(o.get("host_id")) == str(host_id)]
    assert len(host_offenses) >= 1, "Expected offense after simulation"

    offense_id = host_offenses[0]["id"]
    promote = await analyst_client.post(f"/api/v1/offenses/{offense_id}/promote-to-incident")
    assert promote.status_code == 200, promote.text
    body = promote.json()
    assert body.get("incident_id")

    risk = await analyst_client.get(f"/api/v1/hosts/{host_id}/risk")
    assert risk.status_code == 200
    assert "factors" in risk.json()
