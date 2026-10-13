"""Shared simulation execution pipeline."""

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from inspect import isawaitable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.alert_rule import AlertRule
from app.models.event import Event
from app.models.host import Host
from app.models.metric import Metric
from app.models.siem import Offense
from app.models.simulation_run import SimulationRun
from app.models.timeline import AttackTimeline
from app.models.user import User
from app.pipeline.normalizer import EVENT_CATEGORIES, normalize_event_type
from app.schemas.simulation import (
    SimulationAlertInfo,
    SimulationRunResponse,
    SimulationStepInput,
)
from app.services.audit import log_audit
from app.services.correlation_engine import run_correlation_engine
from app.services.detection import run_detection_for_host
from app.services.mitre import enrich_event
from app.services.offense_engine import link_event_to_offense
from app.services.timeline import build_timelines
from app.websocket.manager import ws_manager

logger = logging.getLogger(__name__)

ALLOWED_EVENT_TYPES = frozenset(EVENT_CATEGORIES.keys()) | {"network_flow", "high_cpu", "high_memory", "high_disk", "service_start", "BUFFERED", "REPLAY", "agent_reconnect"}

# Stream pacing: a preset plays out over this window so the attack is watchable
# live instead of landing in the database in a single millisecond burst.
STREAM_MIN_SECONDS = 6.0
STREAM_MAX_SECONDS = 18.0

PACE_INSTANT = "instant"
PACE_STREAM = "stream"
VALID_PACES = (PACE_INSTANT, PACE_STREAM)


@dataclass
class RunStep:
    event_type: str
    offset_seconds: int
    severity: str | None = None
    description: str | None = None


# BUFFERED / REPLAY are scenario markers for the agent_resilience preset, not
# ingestible event types. normalize_event_type() lowercases input, so they can
# never pass validate_steps(); advertising them just makes the custom builder
# default to a value the API rejects with 422.
CUSTOM_EVENT_TYPES = frozenset(
    et for et in ALLOWED_EVENT_TYPES if et not in {"BUFFERED", "REPLAY"}
)


def list_allowed_event_types() -> list[dict]:
    return [
        {"event_type": et, "category": EVENT_CATEGORIES.get(et, "network" if et == "network_flow" else "general")}
        for et in sorted(CUSTOM_EVENT_TYPES)
    ]


def validate_steps(steps: list[SimulationStepInput]) -> list[RunStep]:
    if not steps:
        raise ValueError("At least one step is required")
    if len(steps) > 20:
        raise ValueError("Maximum 20 steps allowed")
    normalized: list[RunStep] = []
    for step in steps:
        etype = normalize_event_type(step.event_type)
        if etype not in ALLOWED_EVENT_TYPES:
            raise ValueError(f"Unsupported event type: {step.event_type}")
        normalized.append(
            RunStep(
                event_type=etype,
                offset_seconds=step.offset_seconds,
                severity=step.severity,
                description=step.description,
            )
        )
    return normalized


def _default_severity(event_type: str) -> str:
    return "medium" if "failure" in event_type else "high"


# Attacker identity used by every simulated external-facing event so alerts
# can name a real source instead of "unknown IP".
SIM_ATTACKER_IP = "198.51.100.23"
SIM_TARGET_USER = "svc_deploy"

_EVENT_DEFAULTS: dict[str, dict] = {
    "ssh_login_failure": {
        "description": "Failed password for {user} from {ip} port 51234 ssh2",
        "source_ip": SIM_ATTACKER_IP,
        "username": SIM_TARGET_USER,
    },
    "ssh_login_success": {
        "description": "Accepted password for {user} from {ip} port 51240 ssh2",
        "source_ip": SIM_ATTACKER_IP,
        "username": SIM_TARGET_USER,
    },
    "root_login": {
        "description": "root login accepted on tty/pts",
        "username": "root",
    },
    "sudo_usage": {
        "description": "sudo: {user} : TTY=pts/0 ; PWD=/home/{user} ; COMMAND=/usr/bin/id",
        "username": SIM_TARGET_USER,
    },
    "firewall_block": {
        "description": "iptables: BLOCK IN={ip} DST=10.0.0.10 PROTO=TCP",
        "source_ip": SIM_ATTACKER_IP,
    },
}


def _build_event_metadata(
    etype: str, run_id: str
) -> tuple[dict, str, str | None, str | None]:
    metadata: dict = {"simulated": True, "simulation_run_id": run_id}
    source_ip: str | None = None
    username: str | None = None
    description = f"[SIMULATED] {etype}"

    defaults = _EVENT_DEFAULTS.get(etype)
    if defaults:
        source_ip = defaults.get("source_ip")
        username = defaults.get("username")
        description = "[SIMULATED] " + defaults["description"].format(
            user=username or SIM_TARGET_USER, ip=source_ip or SIM_ATTACKER_IP
        )

    if etype == "network_flow":
        metadata.update({
            "src_ip": "10.0.0.50",
            "dst_ip": "203.0.113.10",
            "dst_port": 443,
            "protocol": "tcp",
        })
        description = "[SIMULATED] TCP 10.0.0.50 → 203.0.113.10:443"
        source_ip = metadata["src_ip"]

    return metadata, description, source_ip, username


def _render_raw_log(
    host_name: str,
    etype: str,
    timestamp: datetime,
    username: str | None,
    source_ip: str | None,
    description: str | None,
) -> str:
    """Render a syslog-style line so the demo can show raw evidence."""
    ts = timestamp.strftime("%b %d %H:%M:%S")
    ip = source_ip or "unknown"
    user = username or "unknown"
    if etype == "ssh_login_failure":
        return f"{ts} {host_name} sshd[31415]: Failed password for {user} from {ip} port 51234 ssh2"
    if etype == "ssh_login_success":
        return f"{ts} {host_name} sshd[31415]: Accepted password for {user} from {ip} port 51240 ssh2"
    if etype == "root_login":
        return f"{ts} {host_name} sshd[31415]: Accepted password for root from {ip} port 22011 ssh2"
    if etype == "sudo_usage":
        return f"{ts} {host_name} sudo[2201]: {user} : TTY=pts/0 ; PWD=/home/{user} ; COMMAND=/usr/bin/id"
    if etype == "service_failure":
        return f"{ts} {host_name} systemd[1]: nginx.service: Main process exited, status=exited/1/FAILURE"
    if etype == "service_stop":
        return f"{ts} {host_name} systemd[1]: Stopped nginx.service."
    if etype == "service_start":
        return f"{ts} {host_name} systemd[1]: Started nginx.service."
    if etype == "firewall_block":
        return f"{ts} {host_name} kernel: [UFW BLOCK] IN=eth0 SRC={ip} DST=10.0.0.10 PROTO=TCP DPT=443"
    if etype == "agent_disconnect":
        return f"{ts} {host_name} securi-agent[812]: connection to backend lost, flushing buffer"
    return f"{ts} {host_name} securi-agent[812]: {description or etype}"


async def _broadcast_simulated_event(event: Event, host: Host) -> None:
    await ws_manager.broadcast({
        "type": "security_feed",
        "data": {
            "id": str(event.id),
            "host_id": str(host.id),
            "host_name": host.name,
            "event_type": event.event_type,
            "severity": event.severity,
            "category": event.category,
            "username": event.username,
            "source_ip": str(event.source_ip) if event.source_ip else None,
            "description": event.description,
            "raw_log": event.raw_log,
            "timestamp": event.timestamp.isoformat(),
            "normalized_event": event.normalized_event,
        },
    })


# Metric event types that generate Metric records instead of (or alongside) Events
_METRIC_EVENT_TYPES = {"high_cpu", "high_memory", "high_disk"}


async def _create_pressure_metric(
    db: AsyncSession,
    host: Host,
    timestamp: datetime,
) -> Metric:
    """Create a Metric record that will be picked up by the detection engine.

    A simulated host under pressure reports every resource as elevated in the
    same sample, so a single crisis run satisfies the sustained-CPU, memory
    and disk checkers together (they all read the most recent Metric rows).
    """
    metric = Metric(
        host_id=host.id,
        cpu_percent=95.0,
        memory_percent=92.0,
        disk_percent=88.0,
        network_in=1024 * 1024,
        network_out=512 * 1024,
        load_average=[2.5, 1.8, 1.2],
        uptime_seconds=86400,
        recorded_at=timestamp,
    )
    db.add(metric)
    return metric


def _build_delays(
    steps: list[RunStep],
    pace: str,
    duration_seconds: float | None = None,
) -> list[float]:
    """Sleep to apply *before* each step when streaming.

    Offsets keep their relative rhythm; the whole span is compressed into a
    watchable window so a 5-minute attack story plays out live in seconds.
    """
    if pace != PACE_STREAM or not steps:
        return [0.0] * len(steps)

    offsets = [float(s.offset_seconds) for s in steps]
    span = max(offsets) - min(offsets)
    if span <= 0:
        return [0.0] * len(steps)

    if duration_seconds is None:
        duration = min(max(span, STREAM_MIN_SECONDS), STREAM_MAX_SECONDS)
    else:
        duration = max(0.0, float(duration_seconds))

    prev = min(offsets)
    delays: list[float] = []
    for offset in offsets:
        delta = offset - prev
        delays.append(duration * (delta if delta > 0 else 0.0) / span)
        if offset > prev:
            prev = offset
    return delays


async def _commit_and_run_hooks(db: AsyncSession) -> None:
    """Commit mid-run so other sessions see events/alerts as they land.

    Also drains the outbox (WebSocket `new_alert`, search indexing, job
    enqueues) that `get_db` would otherwise only run after the response.
    """
    await db.commit()
    hooks = db.info.pop("post_commit_hooks", [])
    for hook in hooks:
        try:
            result = hook()
            if isawaitable(result):
                await result
        except Exception:
            logger.warning("post-commit hook failed", exc_info=True)


async def load_alert_details(
    db: AsyncSession, alert_ids: list[UUID]
) -> list[SimulationAlertInfo]:
    """Resolve alert rows (with their rule type) so a run can report what fired."""
    if not alert_ids:
        return []
    rows = (
        await db.execute(
            select(Alert, AlertRule.rule_type)
            .join(AlertRule, AlertRule.id == Alert.rule_id, isouter=True)
            .where(Alert.id.in_(alert_ids))
            .order_by(Alert.created_at.asc())
        )
    ).all()
    return [
        SimulationAlertInfo(
            id=alert.id,
            title=alert.title,
            severity=alert.severity,
            rule_type=rule_type,
            mitre_tactic=alert.mitre_tactic,
            mitre_technique_id=alert.mitre_technique_id,
        )
        for alert, rule_type in rows
    ]


async def execute_simulation_run(
    db: AsyncSession,
    host: Host,
    user: User,
    *,
    scenario_id: str,
    name: str,
    steps: list[RunStep],
    pace: str = PACE_INSTANT,
    duration_seconds: float | None = None,
    expected_alerts: list[str] | None = None,
) -> SimulationRunResponse:
    run_id = str(uuid.uuid4())
    run_start = datetime.now(timezone.utc)
    delays = _build_delays(steps, pace, duration_seconds)
    ingested: list[Event] = []

    for delay, step in zip(delays, steps):
        if delay > 0:
            await asyncio.sleep(delay)

        metadata, default_description, source_ip, username = _build_event_metadata(
            step.event_type, run_id
        )
        description = step.description or default_description
        # Streaming stamps real emission time so nothing is future-dated;
        # instant keeps the legacy offset-based scenario clock.
        if pace == PACE_STREAM:
            timestamp = datetime.now(timezone.utc)
        else:
            timestamp = run_start + timedelta(seconds=step.offset_seconds)

        # For metric event types, create a Metric record so detection checkers can find it
        if step.event_type in _METRIC_EVENT_TYPES:
            await _create_pressure_metric(db, host, timestamp)

        # Always create an Event record for tracking and WebSocket broadcast
        event = Event(
            host_id=host.id,
            event_type=step.event_type,
            severity=step.severity or _default_severity(step.event_type),
            description=description,
            source="simulation",
            timestamp=timestamp,
            metadata_=metadata,
            source_ip=source_ip,
            username=username,
            raw_log=_render_raw_log(
                host.name, step.event_type, timestamp, username, source_ip, description
            ),
        )
        enrich_event(event)
        db.add(event)
        ingested.append(event)

        # Publish each event immediately so the feed, offenses and alerts
        # fill in progressively instead of arriving as one burst.
        await db.flush()
        await link_event_to_offense(db, event)
        await run_detection_for_host(db, host, source="simulation")
        await _commit_and_run_hooks(db)
        await _broadcast_simulated_event(event, host)

    await run_correlation_engine(db, host.id)
    await build_timelines(db, host.id)
    await db.flush()

    run_end = datetime.now(timezone.utc)
    window_start = run_start - timedelta(seconds=1)
    window_end = run_end + timedelta(seconds=1)

    event_ids = [e.id for e in ingested]

    alert_ids = list(
        (
            await db.execute(
                select(Alert.id).where(
                    Alert.host_id == host.id,
                    Alert.created_at >= window_start,
                    Alert.created_at <= window_end,
                )
            )
        ).scalars().all()
    )

    timeline_ids = list(
        (
            await db.execute(
                select(AttackTimeline.id).where(
                    AttackTimeline.host_id == host.id,
                    AttackTimeline.created_at >= window_start,
                    AttackTimeline.created_at <= window_end,
                )
            )
        ).scalars().all()
    )

    offense_ids = list(
        (
            await db.execute(
                select(Offense.id).where(
                    Offense.host_id == host.id,
                    Offense.updated_at >= window_start,
                    Offense.updated_at <= window_end,
                )
            )
        ).scalars().all()
    )

    incident_ids: list[UUID] = []
    if offense_ids:
        incident_ids = list(
            (
                await db.execute(
                    select(Offense.incident_id).where(
                        Offense.id.in_(offense_ids),
                        Offense.incident_id.is_not(None),
                    )
                )
            ).scalars().all()
        )

    alerts = await load_alert_details(db, alert_ids)

    run_row = SimulationRun(
        id=UUID(run_id),
        host_id=host.id,
        user_id=user.id,
        scenario_id=scenario_id,
        name=name,
        event_count=len(ingested),
        alert_count=len(alert_ids),
        offense_count=len(offense_ids),
        timeline_count=len(timeline_ids),
        created_at=run_start,
    )
    db.add(run_row)

    await log_audit(
        db,
        "simulation_run",
        user_id=user.id,
        details={
            "scenario": scenario_id,
            "host_id": str(host.id),
            "run_id": run_id,
            "name": name,
        },
    )

    return SimulationRunResponse(
        message=f"Simulation {scenario_id} completed",
        events=len(ingested),
        run_id=UUID(run_id),
        host_id=host.id,
        scenario=scenario_id,
        name=name,
        event_ids=event_ids,
        alert_ids=alert_ids,
        timeline_ids=timeline_ids,
        offense_ids=offense_ids,
        incident_ids=incident_ids,
        alerts=alerts,
        expected_alerts=list(expected_alerts or []),
    )
