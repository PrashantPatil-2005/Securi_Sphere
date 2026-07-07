"""HTTP integration tests for role-based access control."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_viewer_cannot_create_incident(viewer_client: AsyncClient):
    res = await viewer_client.post(
        "/api/v1/incidents",
        json={"title": "RBAC test", "description": "x", "severity": "low"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_analyst_can_create_incident(analyst_client: AsyncClient):
    res = await analyst_client.post(
        "/api/v1/incidents",
        json={"title": "Analyst incident", "description": "test", "severity": "medium"},
    )
    assert res.status_code == 200
    assert res.json()["title"] == "Analyst incident"


@pytest.mark.asyncio
async def test_viewer_cannot_patch_offense_status(viewer_client: AsyncClient):
    res = await viewer_client.patch(
        "/api/v1/offenses/00000000-0000-0000-0000-000000000001/status",
        json={"status": "investigating"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_access_audit(viewer_client: AsyncClient):
    res = await viewer_client.get("/api/v1/audit")
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_access_audit(admin_client: AsyncClient):
    res = await admin_client.get("/api/v1/audit")
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_analyst_can_list_simulation_scenarios(analyst_client: AsyncClient):
    res = await analyst_client.get("/api/v1/simulation/scenarios")
    assert res.status_code == 200
    body = res.json()
    assert "scenarios" in body
    assert "enabled" in body


@pytest.mark.asyncio
async def test_viewer_cannot_list_simulation_scenarios(viewer_client: AsyncClient):
    res = await viewer_client.get("/api/v1/simulation/scenarios")
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_list_simulation_scenarios(admin_client: AsyncClient):
    res = await admin_client.get("/api/v1/simulation/scenarios")
    assert res.status_code == 200
    body = res.json()
    assert "scenarios" in body
    assert "enabled" in body
    assert len(body["scenarios"]) >= 1
    assert "id" in body["scenarios"][0]
    assert "steps" in body["scenarios"][0]


@pytest.mark.asyncio
async def test_viewer_cannot_export_events(viewer_client: AsyncClient):
    res = await viewer_client.get("/api/v1/events/export")
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_analyst_can_export_events(analyst_client: AsyncClient):
    res = await analyst_client.get("/api/v1/events/export?format=json")
    assert res.status_code == 200
