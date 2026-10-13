"""Case Workspace regression: incident-anchored /investigation/workspace.

Regression target: the incident path loaded the linked Offense WITHOUT
eager-loading Offense.links, so _offense_summary() triggered a lazy load inside
the asyncio session -> MissingGreenlet -> HTTP 500 -> the UI showed
"Failed to load data". The alert- and offense-anchored paths always worked,
which is why only ?incident=... broke.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.alert import Alert
from app.models.event import Event
from app.models.host import Host
from app.models.siem import Offense, OffenseEvent
from app.models.user import User


async def _seed_case() -> dict:
    """Create host + event + alert + offense with links, promote to incident."""
    from app.database import async_session
    from app.services.incident_promotion import promote_offense_to_incident

    async with async_session() as db:
        admin = (
            await db.execute(select(User).where(User.email == "admin@test.local"))
        ).scalar_one()
        now = datetime.now(timezone.utc)

        host = Host(
            name=f"case-ws-{uuid4().hex[:8]}",
            hostname="case-ws.test",
            ip_address="10.99.0.10",
            status="online",
            created_by=admin.id,
        )
        db.add(host)
        await db.flush()

        event = Event(
            host_id=host.id,
            event_type="root_login",
            severity="high",
            category="authentication",
            description="Direct root login",
            username="root",
            timestamp=now,
        )
        db.add(event)
        await db.flush()

        alert = Alert(
            host_id=host.id,
            severity="high",
            title="Root login detected",
            description="Direct root login on test host",
            status="open",
            created_at=now,
        )
        db.add(alert)
        await db.flush()

        offense = Offense(
            offense_number=900000 + int(uuid4().int % 100000),
            host_id=host.id,
            title="Security activity: root_login",
            description="Correlated root login activity",
            risk_level="high",
            status="open",
            event_count=1,
            alert_count=1,
            created_at=now,
            updated_at=now,
        )
        db.add(offense)
        await db.flush()

        db.add(OffenseEvent(offense_id=offense.id, event_id=event.id, linked_at=now))
        db.add(OffenseEvent(offense_id=offense.id, alert_id=alert.id, linked_at=now))
        await db.commit()

        result = await promote_offense_to_incident(db, offense.id, admin)
        await db.commit()

        return {
            "host_id": host.id,
            "event_id": event.id,
            "alert_id": alert.id,
            "offense_id": offense.id,
            "incident_id": result["incident_id"],
        }


@pytest.mark.integration
async def test_incident_anchored_workspace_loads(admin_client, prepare_database):
    """?incident_id=... must return the full case (this was the 500)."""
    ids = await _seed_case()
    res = await admin_client.get(
        "/api/v1/investigation/workspace", params={"incident_id": str(ids["incident_id"])}
    )
    assert res.status_code == 200, res.text

    body = res.json()
    assert body["anchor"] == {"type": "incident", "id": ids["incident_id"]}
    assert body["incident"]["id"] == ids["incident_id"]
    assert body["incident"]["host_id"] == str(ids["host_id"])
    assert body["host"]["id"] == str(ids["host_id"])

    # Offense + its linked events/alerts come from Offense.links (the lazy-load hazard).
    assert body["offense"] is not None
    assert body["offense"]["id"] == str(ids["offense_id"])
    assert [e["id"] for e in body["offense"]["events"]] == [str(ids["event_id"])]
    assert body["offense"]["events"][0]["event_type"] == "root_login"
    assert body["offense"]["alerts"][0]["id"] == str(ids["alert_id"])

    assert [a["id"] for a in body["linked_alerts"]] == [str(ids["alert_id"])]
    assert body["alert"]["id"] == str(ids["alert_id"])
    assert any(e["event_type"] == "root_login" for e in body["events"])

    # Phase 8 enrichment: merged timeline, entities, MITRE block, provenance,
    # and honest partial-failure reporting all present on a healthy case.
    assert body["partial_errors"] == []
    types = {e["type"] for e in body["investigation_timeline"]}
    assert "incident" in types
    assert "alert" in types
    assert "event" in types
    assert any(h["name"] == body["host"]["name"] for h in body["entities"]["hosts"])
    assert isinstance(body["mitre"]["technique_ids"], list)
    assert body["provenance"]["simulated"] is False
    assert body["incident"]["assignee_email"] is None
    assert isinstance(body["incident"]["notes"], list)


@pytest.mark.integration
async def test_alert_and_offense_anchors_still_work(admin_client, prepare_database):
    ids = await _seed_case()

    res = await admin_client.get(
        "/api/v1/investigation/workspace", params={"alert_id": str(ids["alert_id"])}
    )
    assert res.status_code == 200, res.text
    assert res.json()["anchor"]["type"] == "alert"

    res = await admin_client.get(
        "/api/v1/investigation/workspace", params={"offense_id": str(ids["offense_id"])}
    )
    assert res.status_code == 200, res.text
    assert res.json()["anchor"]["type"] == "offense"


@pytest.mark.integration
async def test_missing_incident_returns_404(admin_client, prepare_database):
    res = await admin_client.get(
        "/api/v1/investigation/workspace", params={"incident_id": str(uuid4())}
    )
    assert res.status_code == 404
    assert "not found" in res.json()["error"]["message"].lower()


@pytest.mark.integration
async def test_workspace_requires_exactly_one_anchor(admin_client, prepare_database):
    res = await admin_client.get("/api/v1/investigation/workspace")
    assert res.status_code == 400

    res = await admin_client.get(
        "/api/v1/investigation/workspace",
        params={"incident_id": str(uuid4()), "alert_id": str(uuid4())},
    )
    assert res.status_code == 400


@pytest.mark.integration
async def test_workspace_requires_authentication(prepare_database):
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        res = await ac.get(
            "/api/v1/investigation/workspace", params={"incident_id": str(uuid4())}
        )
    assert res.status_code == 401


@pytest.mark.integration
async def test_viewer_role_can_read_workspace(viewer_client, prepare_database):
    """RBAC is unchanged: reading the workspace stays available to every role."""
    ids = await _seed_case()
    res = await viewer_client.get(
        "/api/v1/investigation/workspace", params={"incident_id": str(ids["incident_id"])}
    )
    assert res.status_code == 200, res.text


@pytest.mark.integration
async def test_simulated_case_is_flagged_in_provenance(admin_client, prepare_database):
    """Demo Center cases must be visually distinguishable from live data."""
    from app.database import async_session
    from app.models.incident import Incident

    ids = await _seed_case()
    async with async_session() as db:
        inc = (await db.get(Incident, ids["incident_id"]))
        inc.simulated = True
        inc.source = "simulation"
        inc.mitre_technique_ids = ["T1078"]
        inc.mitre_tactics = ["initial-access"]
        await db.commit()

    res = await admin_client.get(
        "/api/v1/investigation/workspace", params={"incident_id": str(ids["incident_id"])}
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["provenance"]["simulated"] is True
    assert "simulation" in body["provenance"]["sources"]
    assert body["incident"]["simulated"] is True
    assert "T1078" in body["mitre"]["technique_ids"]
    assert "initial-access" in body["mitre"]["tactics"]
    # The timeline carries the same synthetic marker per entry.
    assert any(e["simulated"] for e in body["investigation_timeline"])


@pytest.mark.integration
async def test_incident_assign_and_rbac(analyst_client, viewer_client, prepare_database):
    """Assignment works for analysts, is blocked for viewers, rejects unknown users."""
    from uuid import uuid4

    ids = await _seed_case()

    me = await analyst_client.get("/api/v1/auth/me")
    assert me.status_code == 200
    my_id = me.json()["id"]

    assign = await analyst_client.patch(
        f"/api/v1/incidents/{ids['incident_id']}/assign",
        json={"assigned_to": my_id},
    )
    assert assign.status_code == 200, assign.text
    assert assign.json()["assigned_to"] == my_id

    ws = await analyst_client.get(
        "/api/v1/investigation/workspace", params={"incident_id": str(ids["incident_id"])}
    )
    assert ws.status_code == 200
    assert ws.json()["incident"]["assignee_email"] == "analyst@test.local"

    unassign = await analyst_client.patch(
        f"/api/v1/incidents/{ids['incident_id']}/assign",
        json={"assigned_to": None},
    )
    assert unassign.status_code == 200
    assert unassign.json()["assigned_to"] is None

    unknown = await analyst_client.patch(
        f"/api/v1/incidents/{ids['incident_id']}/assign",
        json={"assigned_to": str(uuid4())},
    )
    assert unknown.status_code == 400

    forbidden = await viewer_client.patch(
        f"/api/v1/incidents/{ids['incident_id']}/assign",
        json={"assigned_to": my_id},
    )
    assert forbidden.status_code == 403
