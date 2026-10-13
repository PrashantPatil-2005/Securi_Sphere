"""Tests for simulation scenario API."""

import time
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.database import async_session
from app.models.alert import Alert
from app.models.alert_rule import AlertRule
from app.models.event import Event
from app.models.simulation_run import SimulationRun
from app.services.simulation_scenarios import SCENARIO_DEFS, get_scenario
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
    expected_count = len(get_scenario("multi_stage_attack").steps)
    assert multi["event_count"] == expected_count
    assert len(multi["steps"]) == expected_count
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
    expected_events = len(get_scenario("brute_force").steps)
    assert body["events"] == expected_events
    assert body["scenario"] == "brute_force"
    assert body["host_id"] == str(host_id)
    assert "run_id" in body
    assert "name" in body
    assert len(body["event_ids"]) == expected_events
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


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario_id", sorted(SCENARIO_DEFS))
async def test_preset_fires_expected_alerts(admin_client: AsyncClient, scenario_id: str):
    """A preset that advertises alerts must actually raise them during a demo."""
    expected = set(get_scenario(scenario_id).expected_alerts)
    if not expected:
        pytest.skip(f"{scenario_id} advertises no alerts")

    host_id = await create_test_host(
        f"sim-expect-{scenario_id}", hostname=f"expect-{scenario_id}"
    )

    res = await admin_client.post(f"/api/v1/simulation/run/{scenario_id}?host_id={host_id}")
    if res.status_code == 403:
        pytest.skip("Simulation disabled in this environment")
    assert res.status_code == 200, res.text

    async with async_session() as db:
        fired = set(
            (
                await db.execute(
                    select(AlertRule.rule_type)
                    .join(Alert, Alert.rule_id == AlertRule.id)
                    .where(Alert.host_id == host_id)
                )
            ).scalars().all()
        )

    assert expected <= fired, (
        f"{scenario_id}: expected alerts {sorted(expected)} but only {sorted(fired)} fired"
    )


@pytest.mark.asyncio
async def test_streamed_run_paces_events_live(admin_client: AsyncClient):
    """pace=stream must spread the attack over time and never future-date events."""
    host_id = await create_test_host("sim-stream-host", hostname="sim-stream")

    started = time.monotonic()
    res = await admin_client.post(
        f"/api/v1/simulation/run/brute_force_only"
        f"?host_id={host_id}&pace=stream&duration_seconds=2"
    )
    elapsed = time.monotonic() - started

    if res.status_code == 403:
        pytest.skip("Simulation disabled in this environment")
    assert res.status_code == 200, res.text
    assert elapsed >= 1.5, f"streamed run finished too fast ({elapsed:.2f}s)"
    assert elapsed < 120, f"streamed run took too long ({elapsed:.2f}s)"

    async with async_session() as db:
        span = (
            await db.execute(
                select(func.max(Event.timestamp) - func.min(Event.timestamp)).where(
                    Event.host_id == host_id
                )
            )
        ).scalar()
        newest = (
            await db.execute(
                select(func.max(Event.timestamp)).where(Event.host_id == host_id)
            )
        ).scalar()

    assert span is not None and span.total_seconds() >= 0.5, (
        f"streamed events landed in a single burst (span={span})"
    )
    assert newest is not None
    assert newest <= datetime.now(timezone.utc) + timedelta(seconds=2), (
        "streamed events must be stamped at emission time, not scheduled in the future"
    )


@pytest.mark.asyncio
async def test_invalid_pace_rejected(admin_client: AsyncClient):
    host_id = await create_test_host("sim-pace-host", hostname="sim-pace")
    res = await admin_client.post(
        f"/api/v1/simulation/run/service_crash?host_id={host_id}&pace=teleport"
    )
    assert res.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scenario_id",
    ["brute_force_only", "service_crash", "host_health_crisis", "multi_stage_attack"],
)
async def test_streamed_run_raises_the_same_alerts_as_instant(
    admin_client: AsyncClient, scenario_id: str
):
    """Streaming must not change detection outcomes — only when they land."""
    expected = set(get_scenario(scenario_id).expected_alerts)
    if not expected:
        pytest.skip(f"{scenario_id} advertises no alerts")

    instant_host = await create_test_host(
        f"sim-inst-{scenario_id}", hostname=f"inst-{scenario_id}"
    )
    stream_host = await create_test_host(
        f"sim-strm-{scenario_id}", hostname=f"strm-{scenario_id}"
    )

    instant = await admin_client.post(
        f"/api/v1/simulation/run/{scenario_id}?host_id={instant_host}&pace=instant"
    )
    if instant.status_code == 403:
        pytest.skip("Simulation disabled in this environment")
    assert instant.status_code == 200, instant.text

    streamed = await admin_client.post(
        f"/api/v1/simulation/run/{scenario_id}"
        f"?host_id={stream_host}&pace=stream&duration_seconds=2"
    )
    assert streamed.status_code == 200, streamed.text

    async def fired(host_id):
        async with async_session() as db:
            return set(
                (
                    await db.execute(
                        select(AlertRule.rule_type)
                        .join(Alert, Alert.rule_id == AlertRule.id)
                        .where(Alert.host_id == host_id)
                    )
                ).scalars().all()
            )

    instant_alerts = await fired(instant_host)
    stream_alerts = await fired(stream_host)

    assert expected <= instant_alerts, (
        f"{scenario_id}: instant run missing {sorted(expected - instant_alerts)}"
    )
    assert instant_alerts == stream_alerts, (
        f"{scenario_id}: instant {sorted(instant_alerts)} != stream {sorted(stream_alerts)}"
    )


@pytest.mark.asyncio
async def test_run_response_reports_what_actually_fired(admin_client: AsyncClient):
    """The run response must describe the alerts it raised, not just their IDs."""
    host_id = await create_test_host("sim-report-host", hostname="sim-report")

    res = await admin_client.post(
        f"/api/v1/simulation/run/brute_force_only?host_id={host_id}&pace=instant"
    )
    if res.status_code == 403:
        pytest.skip("Simulation disabled in this environment")
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["expected_alerts"], "preset should advertise its expected alerts"
    assert body["alerts"], "run response must describe the alerts it raised"

    for alert in body["alerts"]:
        assert alert["title"]
        assert alert["severity"] in {"info", "low", "medium", "high", "critical"}
        assert alert["rule_type"], "fired alerts must carry their rule type"

    fired = {alert["rule_type"] for alert in body["alerts"]}
    assert set(body["expected_alerts"]) <= fired, (
        f"expected {sorted(body['expected_alerts'])} but response only lists {sorted(fired)}"
    )

    # The history view reads the same data through the run-detail endpoint.
    detail = await admin_client.get(f"/api/v1/simulation/runs/{body['run_id']}")
    assert detail.status_code == 200, detail.text
    detail_body = detail.json()
    assert detail_body["expected_alerts"] == body["expected_alerts"]
    assert {a["rule_type"] for a in detail_body["alerts"]} >= set(body["expected_alerts"])


@pytest.mark.asyncio
async def test_simulated_events_expose_raw_log_for_the_tail(admin_client: AsyncClient):
    """The Attack Lab raw-log tail seeds from this endpoint, so it must return syslog lines."""
    host_id = await create_test_host("sim-tail-host", hostname="sim-tail")

    res = await admin_client.post(
        f"/api/v1/simulation/run/service_crash?host_id={host_id}&pace=instant"
    )
    if res.status_code == 403:
        pytest.skip("Simulation disabled in this environment")
    assert res.status_code == 200, res.text

    listed = await admin_client.get(
        f"/api/v1/events?host_id={host_id}&page_size=50&include_simulated=true&sort=newest"
    )
    assert listed.status_code == 200, listed.text
    items = listed.json()["items"]

    assert items, "simulated events must be listable with include_simulated=true"
    missing = [i["event_type"] for i in items if not i.get("raw_log")]
    assert not missing, f"events without a syslog line: {missing}"
    assert all(" sim-tail-host " in i["raw_log"] for i in items), (
        "raw_log should carry the host name like a real syslog line"
    )


@pytest.mark.asyncio
async def test_reset_run_removes_only_that_runs_artifacts(admin_client: AsyncClient):
    """Resetting one run must leave other runs on the same host intact."""
    host_id = await create_test_host("sim-reset-host", hostname="sim-reset")

    first = await admin_client.post(
        f"/api/v1/simulation/run/service_crash?host_id={host_id}&pace=instant"
    )
    if first.status_code == 403:
        pytest.skip("Simulation disabled in this environment")
    assert first.status_code == 200, first.text
    first_body = first.json()

    second = await admin_client.post(
        f"/api/v1/simulation/run/brute_force_only?host_id={host_id}&pace=instant"
    )
    assert second.status_code == 200, second.text
    second_body = second.json()

    res = await admin_client.delete(f"/api/v1/simulation/runs/{first_body['run_id']}")
    assert res.status_code == 200, res.text
    assert res.json()["events_deleted"] == len(first_body["event_ids"])

    # Count straight from the DB: the events API applies a default time window,
    # and instant-mode events can carry future timestamps.
    async with async_session() as db:
        remaining = list(
            (
                await db.execute(
                    select(Event.id).where(
                        Event.host_id == host_id, Event.source == "simulation"
                    )
                )
            ).scalars().all()
        )
    assert len(remaining) == len(second_body["event_ids"]), (
        "reset must not touch another run's events on the same host"
    )

    runs = (await admin_client.get("/api/v1/simulation/runs?page_size=50")).json()["items"]
    run_ids = {r["id"] for r in runs}
    assert first_body["run_id"] not in run_ids
    assert second_body["run_id"] in run_ids


@pytest.mark.asyncio
async def test_replay_reruns_a_preset_and_raises_alerts_again(admin_client: AsyncClient):
    """Replay clears the prior run first so open alerts cannot dedupe it away."""
    host_id = await create_test_host("sim-replay-host", hostname="sim-replay")

    first = await admin_client.post(
        f"/api/v1/simulation/run/brute_force_only?host_id={host_id}&pace=instant"
    )
    if first.status_code == 403:
        pytest.skip("Simulation disabled in this environment")
    assert first.status_code == 200, first.text
    first_body = first.json()
    assert first_body["alerts"], "the original run should raise detections"

    replay = await admin_client.post(
        f"/api/v1/simulation/runs/{first_body['run_id']}/replay"
    )
    assert replay.status_code == 200, replay.text
    replay_body = replay.json()

    assert replay_body["run_id"] != first_body["run_id"]
    assert replay_body["scenario"] == "brute_force_only"
    assert replay_body["alerts"], "a replay must raise detections again"
    assert {a["rule_type"] for a in replay_body["alerts"]} >= set(
        replay_body["expected_alerts"]
    )


@pytest.mark.asyncio
async def test_replay_rejects_custom_runs(admin_client: AsyncClient):
    """Custom runs keep no step list, so they can only be reset, not replayed."""
    host_id = await create_test_host("sim-replay-custom", hostname="sim-replayc")

    created = await admin_client.post(
        "/api/v1/simulation/custom",
        json={
            "host_id": str(host_id),
            "name": "Custom chain",
            "steps": [
                {"event_type": "ssh_login_failure", "offset_seconds": 0},
                {"event_type": "ssh_login_failure", "offset_seconds": 1},
            ],
        },
    )
    if created.status_code == 403:
        pytest.skip("Simulation disabled in this environment")
    assert created.status_code == 200, created.text

    res = await admin_client.post(
        f"/api/v1/simulation/runs/{created.json()['run_id']}/replay"
    )
    assert res.status_code == 422, res.text
    assert "Custom" in str(res.json()), f"unexpected 422 body: {res.text}"


@pytest.mark.asyncio
async def test_reset_unknown_run_is_404(admin_client: AsyncClient):
    res = await admin_client.delete(
        "/api/v1/simulation/runs/00000000-0000-0000-0000-000000000000"
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_purge_keeps_real_data_on_a_host_that_ran_a_simulation(
    admin_client: AsyncClient,
):
    """Purge targets provenance, not hosts: real detections must survive."""
    host_id = await create_test_host("sim-purge-mixed", hostname="sim-purgem")

    async with async_session() as db:
        real_event = Event(
            host_id=host_id,
            event_type="ssh_login_failure",
            severity="medium",
            source="journald",
            raw_log="Failed password for root from 10.0.0.9 port 22 ssh2",
            timestamp=datetime.now(timezone.utc),
        )
        real_alert = Alert(
            host_id=host_id,
            severity="high",
            title="Real detection that must survive",
            status="open",
        )
        db.add(real_event)
        db.add(real_alert)
        await db.flush()
        real_event_id = real_event.id
        real_alert_id = real_alert.id
        await db.commit()

    run = await admin_client.post(
        f"/api/v1/simulation/run/brute_force_only?host_id={host_id}"
    )
    if run.status_code == 403:
        pytest.skip("Simulation disabled in this environment")
    assert run.status_code == 200, run.text

    res = await admin_client.delete("/api/v1/simulation/purge")
    assert res.status_code == 200, res.text
    assert res.json()["events_deleted"] > 0
    assert res.json()["alerts_deleted"] > 0

    async with async_session() as db:
        real_event_still = (
            await db.execute(select(Event).where(Event.id == real_event_id))
        ).scalar_one_or_none()
        real_alert_still = (
            await db.execute(select(Alert).where(Alert.id == real_alert_id))
        ).scalar_one_or_none()
        sim_events = (
            await db.execute(
                select(func.count())
                .select_from(Event)
                .where(Event.source == "simulation")
            )
        ).scalar_one()
        sim_alerts = (
            await db.execute(
                select(func.count())
                .select_from(Alert)
                .where(Alert.source == "simulation")
            )
        ).scalar_one()

    assert real_event_still is not None, "purge must never delete a real event"
    assert real_alert_still is not None, "purge must never delete a real alert"
    assert sim_events == 0
    assert sim_alerts == 0
