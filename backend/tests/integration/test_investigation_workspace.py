"""Integration tests for unified investigation workspace API."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.database import async_session
from app.models.host import Host


@pytest.mark.asyncio
async def test_workspace_requires_single_anchor(admin_client: AsyncClient):
    res = await admin_client.get("/api/v1/investigation/workspace")
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_workspace_from_alert_after_simulation(admin_client: AsyncClient):
    async with async_session() as db:
        host = Host(name="ws-host", hostname="ws-host", status="online")
        db.add(host)
        await db.commit()
        await db.refresh(host)
        host_id = host.id

    sim = await admin_client.post(f"/api/v1/simulation/run/brute_force_only?host_id={host_id}")
    if sim.status_code == 403:
        pytest.skip("Simulation disabled")
    assert sim.status_code == 200

    alerts = await admin_client.get(f"/api/v1/alerts?host_id={host_id}&page_size=5")
    assert alerts.status_code == 200
    items = alerts.json().get("items", [])
    if not items:
        pytest.skip("No alerts generated")
    alert_id = items[0]["id"]

    ws = await admin_client.get(f"/api/v1/investigation/workspace?alert_id={alert_id}")
    assert ws.status_code == 200, ws.text
    body = ws.json()
    assert body["anchor"]["type"] == "alert"
    assert body["anchor"]["id"] == alert_id
    assert body["alert"] is not None
    assert body["host"] is not None
