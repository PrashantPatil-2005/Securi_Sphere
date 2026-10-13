from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.dependencies import require_roles
from app.models.alert import Alert
from app.models.correlation import CorrelationResult
from app.models.event import Event
from app.models.host import Host
from app.models.incident import IncidentAlert
from app.models.siem import Offense, OffenseEvent
from app.models.simulation_run import SimulationRun
from app.models.timeline import AttackTimeline
from app.models.user import User
from app.schemas.simulation import (
    CustomSimulationRequest,
    EventTypesResponse,
    ScenariosListResponse,
    SimulationRunDetail,
    SimulationRunListResponse,
    SimulationRunResponse,
    SimulationRunSummary,
    SimulationStepInput,
)
from app.services.audit import log_audit
from app.services.simulation_runner import (
    PACE_INSTANT,
    VALID_PACES,
    RunStep,
    execute_simulation_run,
    list_allowed_event_types,
    load_alert_details,
    validate_steps,
)
from app.services.simulation_scenarios import (
    SCENARIO_DEFS,
    get_scenario,
    list_scenarios_api,
)

router = APIRouter(prefix="/simulation", tags=["simulation"])

SIMULATION_ROLES = ("admin", "analyst")


@router.get("/scenarios", response_model=ScenariosListResponse)
async def list_scenarios(user: User = Depends(require_roles(*SIMULATION_ROLES))):
    return ScenariosListResponse(
        scenarios=list_scenarios_api(),
        enabled=settings.enable_simulation,
    )


LIVE_HEARTBEAT_RECENT_SECONDS = 90
FLOW_COLLECTOR_ACTIVE_SECONDS = 300


@router.get("/readiness")
async def simulation_readiness(
    scenario_id: str,
    host_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*SIMULATION_ROLES)),
):
    """Operational readiness for running a scenario.

    Synthetic readiness (backend able to inject events) is reported separately
    from live-host readiness. Live readiness requires a genuinely enrolled,
    recently heartbeating host with any required telemetry source active —
    synthetic data never satisfies it.
    """
    scenario = get_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Unknown scenario")

    from app.services.system_health import build_component_status

    components_payload = await build_component_status()
    impaired_components = [
        c["id"] for c in components_payload["components"]
        if c["status"] in ("degraded", "unavailable")
    ]
    # Synthetic injection needs the API + database; queue/search issues do not block it.
    blocking = [c for c in impaired_components if c in ("api", "postgres")]
    synthetic_ready = settings.enable_simulation and not blocking

    required_telemetry = list(scenario.required_telemetry or [])
    requires_flow_collector = any("flow collector" in t.lower() for t in required_telemetry)

    host_payload: dict | None = None
    live_ready = False
    live_reasons: list[str] = []

    if host_id is None:
        live_reasons.append("No host selected for live mode.")
    else:
        host = (
            await db.execute(select(Host).where(Host.id == host_id))
        ).scalar_one_or_none()
        if not host:
            live_reasons.append("Selected host no longer exists.")
        else:
            now = datetime.now(timezone.utc)
            enrolled = bool(host.api_key_hash) and host.api_key_revoked_at is None
            last_seen = host.last_seen
            if last_seen and last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)
            age = (now - last_seen).total_seconds() if last_seen else None
            heartbeat_recent = age is not None and age <= LIVE_HEARTBEAT_RECENT_SECONDS

            flow_active = False
            last_flow = None
            if requires_flow_collector:
                last_flow = (
                    await db.execute(
                        select(func.max(Event.timestamp)).where(
                            Event.host_id == host.id,
                            Event.event_type == "network_flow",
                            Event.timestamp >= now - timedelta(seconds=FLOW_COLLECTOR_ACTIVE_SECONDS),
                        )
                    )
                ).scalar_one_or_none()
                flow_active = last_flow is not None

            host_payload = {
                "host_id": str(host.id),
                "name": host.name,
                "os_info": host.os_info,
                "enrolled": enrolled,
                "heartbeat_state": (
                    "never" if last_seen is None
                    else "recent" if heartbeat_recent
                    else "stale"
                ),
                "heartbeat_age_seconds": age,
                "last_seen": last_seen.isoformat() if last_seen else None,
                "flow_collector_required": requires_flow_collector,
                "flow_collector_active": flow_active if requires_flow_collector else None,
                "provenance": "live",
            }

            if not enrolled:
                live_reasons.append("Host is not enrolled (no active agent credentials).")
            if not heartbeat_recent:
                if last_seen is None:
                    live_reasons.append("Host has never sent a heartbeat.")
                else:
                    live_reasons.append(
                        f"Last heartbeat was {int(age or 0)}s ago — host is not reachable."
                    )
            if requires_flow_collector and not flow_active:
                live_reasons.append(
                    "The flow collector has not delivered network_flow events in the last "
                    f"{FLOW_COLLECTOR_ACTIVE_SECONDS // 60} minutes — enable flow_collector "
                    "in the agent config or wait for the next flow cycle."
                )
            live_ready = not live_reasons

    if not settings.enable_simulation:
        synth_note = "Simulation is disabled (ENABLE_SIMULATION=false)."
    elif synthetic_ready:
        synth_note = "Backend is ready to inject synthetic events for this scenario."
    else:
        synth_note = "Backend dependencies required for synthetic injection are impaired."

    return {
        "scenario_id": scenario.id,
        "scenario_name": scenario.name,
        "required_telemetry": required_telemetry,
        "synthetic_ready": synthetic_ready,
        "synthetic_note": synth_note,
        "live_ready": live_ready,
        "live_reasons": live_reasons,
        "host": host_payload,
        "backend": {
            "overall": components_payload["overall"],
            "impaired_components": impaired_components,
            "timestamp": components_payload["timestamp"],
        },
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/event-types", response_model=EventTypesResponse)
async def list_event_types(user: User = Depends(require_roles(*SIMULATION_ROLES))):
    return EventTypesResponse(event_types=list_allowed_event_types())


@router.get("/runs", response_model=SimulationRunListResponse)
async def list_simulation_runs(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*SIMULATION_ROLES)),
    host_id: UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    filters = []
    if host_id:
        filters.append(SimulationRun.host_id == host_id)

    total = (
        await db.execute(select(func.count()).select_from(SimulationRun).where(*filters))
    ).scalar_one()

    rows = (
        await db.execute(
            select(SimulationRun)
            .where(*filters)
            .options(selectinload(SimulationRun.host), selectinload(SimulationRun.user))
            .order_by(SimulationRun.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    items = [
        SimulationRunSummary(
            id=row.id,
            scenario_id=row.scenario_id,
            name=row.name,
            host_id=row.host_id,
            host_name=row.host.name if row.host else None,
            event_count=row.event_count,
            alert_count=row.alert_count,
            offense_count=row.offense_count,
            timeline_count=row.timeline_count,
            created_at=row.created_at,
            run_by=row.user.email if row.user else None,
        )
        for row in rows
    ]
    return SimulationRunListResponse(items=items, total=total)


async def _event_ids_for_run(db: AsyncSession, run_id: UUID, host_id: UUID, created_at) -> list[UUID]:
    run_id_str = str(run_id)
    events = (
        await db.execute(
            select(Event.id).where(
                Event.source == "simulation",
                Event.host_id == host_id,
                Event.metadata_["simulation_run_id"].astext == run_id_str,
            )
        )
    ).scalars().all()
    if events:
        return list(events)
    return list(
        (
            await db.execute(
                select(Event.id).where(
                    Event.source == "simulation",
                    Event.host_id == host_id,
                    Event.timestamp >= created_at - timedelta(seconds=1),
                    Event.timestamp <= created_at + timedelta(seconds=3601),
                )
            )
        ).scalars().all()
    )


@router.get("/runs/{run_id}", response_model=SimulationRunDetail)
async def get_simulation_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*SIMULATION_ROLES)),
):
    row = (
        await db.execute(
            select(SimulationRun)
            .where(SimulationRun.id == run_id)
            .options(selectinload(SimulationRun.host), selectinload(SimulationRun.user))
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Simulation run not found")

    window_end = row.created_at + timedelta(seconds=5)
    window_start = row.created_at - timedelta(seconds=1)

    event_ids = await _event_ids_for_run(db, row.id, row.host_id, row.created_at)
    alert_ids = list(
        (
            await db.execute(
                select(Alert.id).where(
                    Alert.host_id == row.host_id,
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
                    AttackTimeline.host_id == row.host_id,
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
                    Offense.host_id == row.host_id,
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

    scenario_def = SCENARIO_DEFS.get(row.scenario_id)

    return SimulationRunDetail(
        id=row.id,
        scenario_id=row.scenario_id,
        name=row.name,
        host_id=row.host_id,
        host_name=row.host.name if row.host else None,
        event_count=row.event_count,
        alert_count=row.alert_count,
        offense_count=row.offense_count,
        timeline_count=row.timeline_count,
        created_at=row.created_at,
        run_by=row.user.email if row.user else None,
        event_ids=event_ids,
        alert_ids=alert_ids,
        timeline_ids=timeline_ids,
        offense_ids=offense_ids,
        incident_ids=incident_ids,
        alerts=await load_alert_details(db, alert_ids),
        expected_alerts=list(scenario_def.expected_alerts) if scenario_def else [],
    )


@router.post("/run/{scenario}", response_model=SimulationRunResponse)
async def run_simulation(
    scenario: str,
    host_id: UUID,
    pace: str = Query(
        PACE_INSTANT,
        description="instant = write everything now; stream = replay the attack live over a few seconds",
    ),
    duration_seconds: float | None = Query(
        None, ge=0, le=120, description="Override the streamed replay length"
    ),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*SIMULATION_ROLES)),
):
    if pace not in VALID_PACES:
        raise HTTPException(status_code=422, detail=f"pace must be one of {list(VALID_PACES)}")
    if not settings.enable_simulation:
        raise HTTPException(status_code=403, detail="Simulation disabled in this environment")
    scenario_def = get_scenario(scenario)
    if not scenario_def:
        raise HTTPException(status_code=404, detail="Unknown scenario")
    host = (await db.execute(select(Host).where(Host.id == host_id))).scalar_one_or_none()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    steps = [
        RunStep(event_type=s.event_type, offset_seconds=s.offset_seconds, severity=s.severity, description=s.description)
        for s in scenario_def.steps
    ]
    return await execute_simulation_run(
        db,
        host,
        user,
        scenario_id=scenario,
        name=scenario_def.name,
        steps=steps,
        pace=pace,
        duration_seconds=duration_seconds,
        expected_alerts=scenario_def.expected_alerts,
    )


@router.post("/custom", response_model=SimulationRunResponse)
async def run_custom_simulation(
    body: CustomSimulationRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*SIMULATION_ROLES)),
):
    if body.pace not in VALID_PACES:
        raise HTTPException(status_code=422, detail=f"pace must be one of {list(VALID_PACES)}")
    if not settings.enable_simulation:
        raise HTTPException(status_code=403, detail="Simulation disabled in this environment")
    host = (await db.execute(select(Host).where(Host.id == body.host_id))).scalar_one_or_none()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    try:
        steps = validate_steps([
            SimulationStepInput(
                event_type=s.event_type,
                offset_seconds=s.offset_seconds,
                severity=s.severity,
                description=s.description,
            )
            for s in body.steps
        ])
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return await execute_simulation_run(
        db,
        host,
        user,
        scenario_id="custom",
        name=body.name,
        steps=steps,
        pace=body.pace,
        duration_seconds=body.duration_seconds,
        expected_alerts=[],
    )


async def _reset_simulation_run(db: AsyncSession, run: SimulationRun) -> dict[str, int]:
    """Remove one run's artifacts without touching other runs on the host."""
    window_start = run.created_at - timedelta(seconds=1)
    window_end = run.created_at + timedelta(seconds=3605)

    event_ids = await _event_ids_for_run(db, run.id, run.host_id, run.created_at)

    alert_ids = list(
        (
            await db.execute(
                select(Alert.id).where(
                    Alert.host_id == run.host_id,
                    Alert.created_at >= window_start,
                    Alert.created_at <= window_end,
                )
            )
        ).scalars().all()
    )

    # Offense links point at both events and alerts, so clear them before either goes.
    link_filters = []
    if event_ids:
        link_filters.append(OffenseEvent.event_id.in_(event_ids))
    if alert_ids:
        link_filters.append(OffenseEvent.alert_id.in_(alert_ids))

    offense_events_deleted = 0
    if link_filters:
        offense_events_deleted = (
            await db.execute(delete(OffenseEvent).where(or_(*link_filters)))
        ).rowcount or 0

    if event_ids:
        await db.execute(delete(Event).where(Event.id.in_(event_ids)))

    alerts_deleted = 0
    if alert_ids:
        alerts_deleted = (
            await db.execute(delete(Alert).where(Alert.id.in_(alert_ids)))
        ).rowcount or 0

    timelines_deleted = (
        await db.execute(
            delete(AttackTimeline).where(
                AttackTimeline.host_id == run.host_id,
                AttackTimeline.created_at >= window_start,
                AttackTimeline.created_at <= window_end,
            )
        )
    ).rowcount or 0

    # An offense that no longer references any event was built purely from this run.
    empty_offense_ids = (
        await db.execute(
            select(Offense.id)
            .outerjoin(OffenseEvent, OffenseEvent.offense_id == Offense.id)
            .where(Offense.host_id == run.host_id, OffenseEvent.id.is_(None))
        )
    ).scalars().all()

    offenses_deleted = 0
    if empty_offense_ids:
        offenses_deleted = (
            await db.execute(delete(Offense).where(Offense.id.in_(empty_offense_ids)))
        ).rowcount or 0

    await db.execute(delete(SimulationRun).where(SimulationRun.id == run.id))
    await db.flush()

    return {
        "events_deleted": len(event_ids),
        "alerts_deleted": alerts_deleted,
        "timelines_deleted": timelines_deleted,
        "offense_events_deleted": offense_events_deleted,
        "offenses_deleted": offenses_deleted,
    }


async def _load_run_or_404(db: AsyncSession, run_id: UUID) -> SimulationRun:
    row = (
        await db.execute(select(SimulationRun).where(SimulationRun.id == run_id))
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Simulation run not found")
    return row


@router.delete("/runs/{run_id}", status_code=200)
async def reset_simulation_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*SIMULATION_ROLES)),
):
    """Remove a single run — its events, alerts, timelines and orphaned offenses."""
    run = await _load_run_or_404(db, run_id)
    counts = await _reset_simulation_run(db, run)

    await log_audit(
        db,
        "simulation_run_reset",
        user_id=user.id,
        details={"run_id": str(run_id), "scenario": run.scenario_id, **counts},
    )
    return {"message": f"Reset run {run.name}", "run_id": run_id, **counts}


@router.post("/runs/{run_id}/replay", response_model=SimulationRunResponse)
async def replay_simulation_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*SIMULATION_ROLES)),
):
    """Re-run a preset from scratch: clear what that run produced, then inject again.

    Resetting first is deliberate — it keeps open alerts from deduplicating the
    replay away, so the second run raises detections just like the first.
    """
    run = await _load_run_or_404(db, run_id)

    if run.scenario_id == "custom":
        raise HTTPException(
            status_code=422,
            detail="Custom runs store no step list — rebuild the chain in the Custom tab",
        )

    scenario_def = get_scenario(run.scenario_id)
    if not scenario_def:
        raise HTTPException(status_code=404, detail="Unknown scenario for this run")

    host = (
        await db.execute(select(Host).where(Host.id == run.host_id))
    ).scalar_one_or_none()
    if not host:
        raise HTTPException(status_code=404, detail="Host for this run no longer exists")

    await _reset_simulation_run(db, run)
    await db.commit()

    steps = [
        RunStep(
            event_type=s.event_type,
            offset_seconds=s.offset_seconds,
            severity=s.severity,
            description=s.description,
        )
        for s in scenario_def.steps
    ]
    return await execute_simulation_run(
        db,
        host,
        user,
        scenario_id=scenario_def.id,
        name=scenario_def.name,
        steps=steps,
        pace="stream",
        expected_alerts=scenario_def.expected_alerts,
    )


@router.delete("/purge")
async def purge_simulated_data(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    """Remove synthetic simulation data without touching real detections.

    Everything is identified by provenance (`Event.source` / `Alert.source`
    membership), never by host or time window, so a host that carries both real
    and simulated data keeps its real alerts, timelines and offenses.
    """
    sim_event_rows = (
        await db.execute(
            select(Event.id, Event.host_id).where(Event.source == "simulation")
        )
    ).all()
    sim_event_ids = [row[0] for row in sim_event_rows]
    sim_event_id_strs = {str(event_id) for event_id in sim_event_ids}

    sim_alert_ids = list(
        (
            await db.execute(select(Alert.id).where(Alert.source == "simulation"))
        ).scalars().all()
    )

    # Timelines are synthetic only when every event they cite is synthetic.
    sim_timeline_ids = [
        timeline.id
        for timeline in (await db.execute(select(AttackTimeline))).scalars().all()
        if timeline.event_ids and set(timeline.event_ids) <= sim_event_id_strs
    ]

    sim_offense_ids: set[UUID] = set()
    offense_filters = []
    if sim_event_ids:
        offense_filters.append(OffenseEvent.event_id.in_(sim_event_ids))
    if sim_alert_ids:
        offense_filters.append(OffenseEvent.alert_id.in_(sim_alert_ids))
    if offense_filters:
        sim_offense_ids = set(
            (
                await db.execute(
                    select(OffenseEvent.offense_id).where(or_(*offense_filters))
                )
            ).scalars().all()
        )

    # Detach every reference before the referenced rows go away.
    if sim_alert_ids:
        await db.execute(
            delete(IncidentAlert).where(IncidentAlert.alert_id.in_(sim_alert_ids))
        )
        await db.execute(
            update(CorrelationResult)
            .where(CorrelationResult.alert_id.in_(sim_alert_ids))
            .values(alert_id=None)
        )
    if offense_filters:
        await db.execute(delete(OffenseEvent).where(or_(*offense_filters)))

    events_deleted = 0
    if sim_event_ids:
        events_deleted = (
            await db.execute(delete(Event).where(Event.id.in_(sim_event_ids)))
        ).rowcount or 0

    alerts_deleted = 0
    if sim_alert_ids:
        alerts_deleted = (
            await db.execute(delete(Alert).where(Alert.id.in_(sim_alert_ids)))
        ).rowcount or 0

    timelines_deleted = 0
    if sim_timeline_ids:
        timelines_deleted = (
            await db.execute(
                delete(AttackTimeline).where(AttackTimeline.id.in_(sim_timeline_ids))
            )
        ).rowcount or 0

    # Offenses that only ever linked simulated rows are now empty.
    offenses_deleted = 0
    if sim_offense_ids:
        still_linked = set(
            (
                await db.execute(
                    select(OffenseEvent.offense_id).where(
                        OffenseEvent.offense_id.in_(list(sim_offense_ids))
                    )
                )
            ).scalars().all()
        )
        empty_offense_ids = [oid for oid in sim_offense_ids if oid not in still_linked]
        if empty_offense_ids:
            offenses_deleted = (
                await db.execute(
                    delete(Offense).where(Offense.id.in_(empty_offense_ids))
                )
            ).rowcount or 0

    runs_deleted = (
        await db.execute(delete(SimulationRun))
    ).rowcount or 0

    await log_audit(
        db,
        "simulation_purge",
        user_id=user.id,
        details={
            "events_deleted": events_deleted,
            "runs_deleted": runs_deleted,
            "timelines_deleted": timelines_deleted,
            "alerts_deleted": alerts_deleted,
            "offenses_deleted": offenses_deleted,
        },
    )
    return {
        "message": "Simulated data removed",
        "events_deleted": events_deleted,
        "runs_deleted": runs_deleted,
        "timelines_deleted": timelines_deleted,
        "alerts_deleted": alerts_deleted,
        "offenses_deleted": offenses_deleted,
    }
