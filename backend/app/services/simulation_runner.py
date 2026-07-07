"""Shared simulation execution pipeline."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.event import Event
from app.models.host import Host
from app.models.siem import Offense
from app.models.simulation_run import SimulationRun
from app.models.timeline import AttackTimeline
from app.models.user import User
from app.pipeline.normalizer import EVENT_CATEGORIES, normalize_event_type
from app.schemas.simulation import SimulationRunResponse, SimulationStepInput
from app.services.audit import log_audit
from app.services.correlation_engine import run_correlation_engine
from app.services.detection import run_detection_for_host
from app.services.mitre import enrich_event
from app.services.offense_engine import link_event_to_offense
from app.services.timeline import build_timelines
from app.websocket.manager import ws_manager

ALLOWED_EVENT_TYPES = frozenset(EVENT_CATEGORIES.keys()) | {"network_flow"}


@dataclass
class RunStep:
    event_type: str
    offset_seconds: int
    severity: str | None = None
    description: str | None = None


def list_allowed_event_types() -> list[dict]:
    return [
        {"event_type": et, "category": EVENT_CATEGORIES.get(et, "network" if et == "network_flow" else "general")}
        for et in sorted(ALLOWED_EVENT_TYPES)
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


def _build_event_metadata(etype: str, run_id: str) -> tuple[dict, str, str | None]:
    metadata: dict = {"simulated": True, "simulation_run_id": run_id}
    description = f"[SIMULATED] {etype}"
    source_ip = None
    if etype == "network_flow":
        metadata.update({
            "src_ip": "10.0.0.50",
            "dst_ip": "203.0.113.10",
            "dst_port": 443,
            "protocol": "tcp",
        })
        description = "[SIMULATED] TCP 10.0.0.50 → 203.0.113.10:443"
        source_ip = metadata["src_ip"]
    return metadata, description, source_ip


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
            "timestamp": event.timestamp.isoformat(),
            "normalized_event": event.normalized_event,
        },
    })


async def execute_simulation_run(
    db: AsyncSession,
    host: Host,
    user: User,
    *,
    scenario_id: str,
    name: str,
    steps: list[RunStep],
) -> SimulationRunResponse:
    run_id = str(uuid.uuid4())
    run_start = datetime.now(timezone.utc)
    ingested: list[Event] = []

    for step in steps:
        metadata, default_description, source_ip = _build_event_metadata(step.event_type, run_id)
        description = step.description or default_description
        event = Event(
            host_id=host.id,
            event_type=step.event_type,
            severity=step.severity or _default_severity(step.event_type),
            description=description,
            source="simulation",
            timestamp=run_start + timedelta(seconds=step.offset_seconds),
            metadata_=metadata,
            source_ip=source_ip,
        )
        enrich_event(event)
        db.add(event)
        ingested.append(event)

    await db.flush()

    for event in ingested:
        await link_event_to_offense(db, event)
        await _broadcast_simulated_event(event, host)

    await run_detection_for_host(db, host)
    await run_correlation_engine(db, host.id)
    await build_timelines(db, host.id)
    await db.flush()

    event_ids = [e.id for e in ingested]

    alert_ids = list(
        (
            await db.execute(
                select(Alert.id).where(
                    Alert.host_id == host.id,
                    Alert.created_at >= run_start - timedelta(seconds=1),
                )
            )
        ).scalars().all()
    )

    timeline_ids = list(
        (
            await db.execute(
                select(AttackTimeline.id).where(
                    AttackTimeline.host_id == host.id,
                    AttackTimeline.created_at >= run_start - timedelta(seconds=1),
                )
            )
        ).scalars().all()
    )

    offense_ids = list(
        (
            await db.execute(
                select(Offense.id).where(
                    Offense.host_id == host.id,
                    Offense.updated_at >= run_start - timedelta(seconds=1),
                )
            )
        ).scalars().all()
    )

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
    )
