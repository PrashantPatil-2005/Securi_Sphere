"""HTTP integration tests for offense promotion."""

from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.database import async_session
from app.models.host import Host
from app.models.siem import Offense


@pytest.mark.asyncio
async def test_viewer_cannot_promote_offense(viewer_client: AsyncClient):
    res = await viewer_client.post(
        "/api/v1/offenses/00000000-0000-0000-0000-000000000001/promote-to-incident",
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_promote_offense_creates_incident(analyst_client: AsyncClient):
    async with async_session() as db:
        host = Host(name="promo-test-host", hostname="promo-test", status="online")
        db.add(host)
        await db.flush()
        offense = Offense(
            offense_number=int(datetime.now().timestamp()) % 1_000_000,
            host_id=host.id,
            title="Test promotion offense",
            description="Integration test",
            risk_level="high",
            status="open",
            event_count=1,
            alert_count=0,
        )
        db.add(offense)
        await db.commit()
        offense_id = offense.id

    res = await analyst_client.post(f"/api/v1/offenses/{offense_id}/promote-to-incident")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["created"] is True
    assert body["incident_id"]

    res2 = await analyst_client.post(f"/api/v1/offenses/{offense_id}/promote-to-incident")
    assert res2.status_code == 200
    assert res2.json()["created"] is False
    assert res2.json()["incident_id"] == body["incident_id"]

    detail = await analyst_client.get(f"/api/v1/incidents/{body['incident_id']}")
    assert detail.status_code == 200
    assert "Offense #" in detail.json()["title"]
