"""Tests for simulation scenario API."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.database import async_session
from app.models.simulation_run import SimulationRun
from tests.integration.helpers import create_test_host


@pytest.mark.asyncio
async def test_admin_scenarios_returns_rich_metadata(admin_client: AsyncClient):
    res = await admin_client.get("/api/v1/simulation/scenarios")
    assert res.status_code == 200
    body = res.json()
    assert "enabled" in body
    assert isinstance(body["scenarios"], list)
    assert len(body["scenarios"]) >= 4

    multi = next(s for s in body["scenarios"] if s["id"] == "multi_stage_attack")
    assert multi["name"] == "Multi-Stage Attack"
    assert multi["difficulty"] == "advanced"
    assert multi["event_count"] == 9
    assert len(multi["steps"]) == 9
    assert multi["steps"][0]["order"] == 1
    assert multi["steps"][0]["event_type"] == "ssh_login_failure"
    assert multi["steps"][0]["mitre"]["technique_id"] == "T1110.001"
    assert "offense" in multi["expected_outcomes"]


@pytest.mark.asyncio
async def test_event_types_list(admin_client: AsyncClient):
    res = await admin_client.get("/api/v1/simulation/event-types")
    assert res.status_code == 200
    types = res.json()["event_types"]
    assert len(types) >= 5
    assert any(t["event_type"] == "ssh_login_failure" for t in types)


@pytest.mark.asyncio
async def test_simulation_run_returns_ids(admin_client: AsyncClient):
    host_id = await create_test_host("sim-api-host", hostname="sim-api")

    res = await admin_client.post(f"/api/v1/simulation/run/brute_force?host_id={host_id}")
    if res.status_code == 403:
        pytest.skip("Simulation disabled in this environment")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["events"] == 7
    assert body["scenario"] == "brute_force"
    assert body["host_id"] == str(host_id)
    assert "run_id" in body
    assert "name" in body
    assert len(body["event_ids"]) == 7
    assert isinstance(body["alert_ids"], list)
    assert isinstance(body["timeline_ids"], list)
    assert isinstance(body["offense_ids"], list)

    runs = await admin_client.get("/api/v1/simulation/runs")
    assert runs.status_code == 200
    assert runs.json()["total"] >= 1

    detail = await admin_client.get(f"/api/v1/simulation/runs/{body['run_id']}")
    assert detail.status_code == 200
    assert detail.json()["id"] == body["run_id"]


@pytest.mark.asyncio
async def test_custom_simulation_run(admin_client: AsyncClient):
    host_id = await create_test_host("sim-custom-host", hostname="sim-custom")

    res = await admin_client.post(
        "/api/v1/simulation/custom",
        json={
            "host_id": str(host_id),
            "name": "Test custom chain",
            "steps": [
                {"event_type": "ssh_login_failure", "offset_seconds": 0},
                {"event_type": "ssh_login_success", "offset_seconds": 30},
            ],
        },
    )
    if res.status_code == 403:
        pytest.skip("Simulation disabled in this environment")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["scenario"] == "custom"
    assert body["name"] == "Test custom chain"
    assert body["events"] == 2

    async with async_session() as db:
        row = (await db.execute(select(SimulationRun).where(SimulationRun.id == body["run_id"]))).scalar_one_or_none()
        assert row is not None
        assert row.scenario_id == "custom"


@pytest.mark.asyncio
async def test_custom_simulation_invalid_event_type(admin_client: AsyncClient):
    host_id = await create_test_host("sim-bad-host", hostname="sim-bad")

    res = await admin_client.post(
        "/api/v1/simulation/custom",
        json={
            "host_id": str(host_id),
            "name": "Bad chain",
            "steps": [{"event_type": "not_a_real_type", "offset_seconds": 0}],
        },
    )
    if res.status_code == 403:
        pytest.skip("Simulation disabled in this environment")
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_analyst_can_run_simulation(analyst_client: AsyncClient):
    host_id = await create_test_host("sim-analyst-host", hostname="sim-analyst")

    scenarios = await analyst_client.get("/api/v1/simulation/scenarios")
    assert scenarios.status_code == 200

    res = await analyst_client.post(f"/api/v1/simulation/run/brute_force_only?host_id={host_id}")
    if res.status_code == 403:
        pytest.skip("Simulation disabled in this environment")
    assert res.status_code == 200, res.text


@pytest.mark.asyncio
async def test_viewer_cannot_purge_simulation(viewer_client: AsyncClient):
    res = await viewer_client.delete("/api/v1/simulation/purge")
    assert res.status_code == 403
