"""Phase 9: operational visibility — component health, agent status, readiness."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

VALID_STATES = {"healthy", "degraded", "unavailable", "unknown"}


# ---------------------------------------------------------------------------
# GET /system/health/components
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_components_admin_only(analyst_client: AsyncClient, admin_client: AsyncClient):
    denied = await analyst_client.get("/api/v1/system/health/components")
    assert denied.status_code == 403

    ok = await admin_client.get("/api/v1/system/health/components")
    assert ok.status_code == 200


@pytest.mark.asyncio
async def test_components_always_200_with_4state_vocabulary(admin_client: AsyncClient):
    res = await admin_client.get("/api/v1/system/health/components")
    assert res.status_code == 200  # dashboard API: always 200, never 5xx for degraded deps
    body = res.json()
    assert body["overall"] in VALID_STATES
    assert "timestamp" in body
    components = body["components"]
    ids = [c["id"] for c in components]
    for expected in ("api", "postgres", "redis", "job_queue", "search", "websocket"):
        assert expected in ids, f"missing component {expected}"
    for c in components:
        assert c["status"] in VALID_STATES
        assert isinstance(c["message"], str) and c["message"]
        assert isinstance(c["impaired"], list)
        # safe diagnostics: no secrets or connection strings in message
        lowered = c["message"].lower()
        for banned in ("password", "postgres://", "redis://", "://user:", "traceback"):
            assert banned not in lowered, f"unsafe diagnostic in {c['id']}: {c['message']}"


@pytest.mark.asyncio
async def test_components_overall_is_worst_of_parts(admin_client: AsyncClient):
    body = (await admin_client.get("/api/v1/system/health/components")).json()
    statuses = [c["status"] for c in body["components"]]
    rank = {"healthy": 0, "unknown": 1, "degraded": 2, "unavailable": 3}
    assert rank[body["overall"]] == max(rank[s] for s in statuses)


# ---------------------------------------------------------------------------
# GET /hosts/{id}/agent-status
# ---------------------------------------------------------------------------


async def _create_host(client: AsyncClient, name: str) -> str:
    res = await client.post("/api/v1/hosts", json={"name": name})
    assert res.status_code in (200, 201), res.text
    return res.json()["id"]


@pytest.mark.asyncio
async def test_agent_status_unenrolled_host(admin_client: AsyncClient):
    host_id = await _create_host(admin_client, f"ops-visibility-{uuid4().hex[:6]}")
    res = await admin_client.get(f"/api/v1/hosts/{host_id}/agent-status")
    assert res.status_code == 200
    body = res.json()
    assert body["host_id"] == host_id
    assert body["enrolled"] is False
    assert body["heartbeat_state"] == "never"
    assert body["delivery_stats"] is None
    assert body["delivery_stats_source"] is None
    assert body["agent_version"] is None
    assert isinstance(body["messages"], list)


@pytest.mark.asyncio
async def test_agent_status_unknown_host_404(admin_client: AsyncClient):
    res = await admin_client.get(f"/api/v1/hosts/{uuid4()}/agent-status")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_agent_status_reflects_heartbeat_and_delivery(admin_client: AsyncClient):
    from app.database import async_session
    from app.models.host import Host

    host_id = await _create_host(admin_client, f"ops-hb-{uuid4().hex[:6]}")
    async with async_session() as db:
        host = await db.get(Host, UUID(host_id))
        host.last_seen = datetime.now(timezone.utc) - timedelta(seconds=10)
        host.agent_version = "3.0.0"
        host.delivery_stats = {
            "buffered_events": 4,
            "last_flush_at": "2026-01-01T00:00:00Z",
            "last_success_at": "2026-01-01T00:00:00Z",
            "consecutive_failures": 0,
            "dropped_events": 1,
            "auth_failed": False,
            "flows_enabled": True,
        }
        await db.commit()

    res = await admin_client.get(f"/api/v1/hosts/{host_id}/agent-status")
    assert res.status_code == 200
    body = res.json()
    assert body["heartbeat_state"] == "recent"
    assert body["agent_version"] == "3.0.0"
    assert body["delivery_stats"]["buffered_events"] == 4
    assert body["delivery_stats"]["dropped_events"] == 1
    assert body["delivery_stats_source"] == "agent_heartbeat"


@pytest.mark.asyncio
async def test_agent_status_stale_heartbeat(admin_client: AsyncClient):
    from app.database import async_session
    from app.models.host import Host

    host_id = await _create_host(admin_client, f"ops-stale-{uuid4().hex[:6]}")
    async with async_session() as db:
        host = await db.get(Host, UUID(host_id))
        host.last_seen = datetime.now(timezone.utc) - timedelta(minutes=10)
        await db.commit()

    res = await admin_client.get(f"/api/v1/hosts/{host_id}/agent-status")
    assert res.status_code == 200
    assert res.json()["heartbeat_state"] == "stale"


# ---------------------------------------------------------------------------
# GET /simulation/readiness
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_readiness_requires_simulation_roles(viewer_client: AsyncClient, analyst_client: AsyncClient):
    denied = await viewer_client.get("/api/v1/simulation/readiness?scenario_id=brute_force_attack")
    assert denied.status_code == 403

    ok = await analyst_client.get("/api/v1/simulation/readiness?scenario_id=brute_force_attack")
    assert ok.status_code == 200


@pytest.mark.asyncio
async def test_readiness_unknown_scenario_404(analyst_client: AsyncClient):
    res = await analyst_client.get("/api/v1/simulation/readiness?scenario_id=does_not_exist")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_readiness_shape_and_synthetic_live_split(analyst_client: AsyncClient):
    res = await analyst_client.get("/api/v1/simulation/readiness?scenario_id=brute_force_attack")
    assert res.status_code == 200
    body = res.json()
    assert body["scenario_id"] == "brute_force_attack"
    assert isinstance(body["synthetic_ready"], bool)
    assert isinstance(body["live_ready"], bool)
    assert body["live_ready"] is False  # no host selected
    assert any("host" in r.lower() for r in body["live_reasons"])
    assert body["host"] is None
    assert isinstance(body["required_telemetry"], list)
    assert body["backend"]["overall"] in VALID_STATES
    assert "synthetic_note" in body


@pytest.mark.asyncio
async def test_readiness_requires_enrolled_recent_host(analyst_client: AsyncClient, admin_client: AsyncClient):
    host_id = await _create_host(admin_client, f"ops-ready-{uuid4().hex[:6]}")
    res = await analyst_client.get(
        f"/api/v1/simulation/readiness?scenario_id=brute_force_attack&host_id={host_id}"
    )
    assert res.status_code == 200
    body = res.json()
    assert body["live_ready"] is False
    assert body["host"]["enrolled"] is False
    reasons_l = " ".join(body["live_reasons"]).lower()
    assert "enroll" in reasons_l or "heartbeat" in reasons_l


@pytest.mark.asyncio
async def test_readiness_scenario_e_requires_flow_collector(analyst_client: AsyncClient, admin_client: AsyncClient):
    # No host: required_telemetry is still exposed
    res = await analyst_client.get(
        "/api/v1/simulation/readiness?scenario_id=network_reconnaissance"
    )
    assert res.status_code == 200
    body = res.json()
    assert any("flow" in t.lower() for t in body["required_telemetry"])
    assert body["live_ready"] is False

    # With a host that has no flow events, the flow reason is explicit
    host_id = await _create_host(admin_client, f"ops-flow-{uuid4().hex[:6]}")
    res = await analyst_client.get(
        f"/api/v1/simulation/readiness?scenario_id=network_reconnaissance&host_id={host_id}"
    )
    assert res.status_code == 200
    body = res.json()
    assert body["live_ready"] is False
    assert body["host"]["flow_collector_required"] is True
    assert body["host"]["flow_collector_active"] is False
    assert any("flow" in r.lower() for r in body["live_reasons"])


# ---------------------------------------------------------------------------
# sanitize_delivery_stats unit checks
# ---------------------------------------------------------------------------


def test_sanitize_delivery_stats_strips_unknown_and_oversized():
    from app.routers.agent import sanitize_delivery_stats

    cleaned = sanitize_delivery_stats(
        {
            "buffered_events": 12,
            "consecutive_failures": 1,
            "dropped_events": 0,
            "last_flush_at": "2026-01-01T00:00:00Z",
            "last_success_at": "2026-01-01T00:00:00Z",
            "auth_failed": False,
            "flows_enabled": True,
            "token": "super-secret",  # must be stripped
            "last_success_at_x": "x" * 500,  # unknown key stripped
            "buffered_events_bad": "not-an-int",
        }
    )
    assert cleaned is not None
    assert cleaned["buffered_events"] == 12
    assert "token" not in cleaned
    assert "last_success_at_x" not in cleaned
    assert "buffered_events_bad" not in cleaned


def test_sanitize_delivery_stats_none_passthrough():
    from app.routers.agent import sanitize_delivery_stats

    assert sanitize_delivery_stats(None) is None
    assert sanitize_delivery_stats("not-a-dict") is None
    assert sanitize_delivery_stats({}) is None  # no known fields → nothing to store
    assert sanitize_delivery_stats({"token": "x"}) is None  # only unknown keys → nothing to store
