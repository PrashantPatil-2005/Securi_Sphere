from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.dependencies import require_roles
from app.models.alert import Alert
from app.models.event import Event
from app.models.host import Host
from app.models.siem import Offense
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
    RunStep,
    execute_simulation_run,
    list_allowed_event_types,
    validate_steps,
)
from app.services.simulation_scenarios import get_scenario, list_scenarios_api

router = APIRouter(prefix="/simulation", tags=["simulation"])

SIMULATION_ROLES = ("admin", "analyst")


@router.get("/scenarios", response_model=ScenariosListResponse)
async def list_scenarios(user: User = Depends(require_roles(*SIMULATION_ROLES))):
    return ScenariosListResponse(
        scenarios=list_scenarios_api(),
        enabled=settings.enable_simulation,
    )


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
    )


@router.post("/run/{scenario}", response_model=SimulationRunResponse)
async def run_simulation(
    scenario: str,
    host_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*SIMULATION_ROLES)),
):
    if not settings.enable_simulation:
        raise HTTPException(status_code=403, detail="Simulation disabled in this environment")
    scenario_def = get_scenario(scenario)
    if not scenario_def:
        raise HTTPException(status_code=404, detail="Unknown scenario")
    host = (await db.execute(select(Host).where(Host.id == host_id))).scalar_one_or_none()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    steps = [
        RunStep(event_type=s.event_type, offset_seconds=s.offset_seconds, description=s.description)
        for s in scenario_def.steps
    ]
    return await execute_simulation_run(
        db,
        host,
        user,
        scenario_id=scenario,
        name=scenario_def.name,
        steps=steps,
    )


@router.post("/custom", response_model=SimulationRunResponse)
async def run_custom_simulation(
    body: CustomSimulationRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*SIMULATION_ROLES)),
):
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
    )


@router.delete("/purge")
async def purge_simulated_data(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    """Remove all synthetic simulation events and related demo artifacts."""
    sim_host_ids = (
        await db.execute(select(Event.host_id).where(Event.source == "simulation").distinct())
    ).scalars().all()

    events_deleted = (
        await db.execute(delete(Event).where(Event.source == "simulation"))
    ).rowcount or 0

    runs_deleted = (
        await db.execute(delete(SimulationRun))
    ).rowcount or 0

    timelines_deleted = 0
    alerts_deleted = 0
    if sim_host_ids:
        timelines_deleted = (
            await db.execute(delete(AttackTimeline).where(AttackTimeline.host_id.in_(sim_host_ids)))
        ).rowcount or 0
        alerts_deleted = (
            await db.execute(
                delete(Alert).where(
                    Alert.host_id.in_(sim_host_ids),
                    Alert.status.in_(["open", "investigating"]),
                )
            )
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
        },
    )
    return {
        "message": "Simulated data removed",
        "events_deleted": events_deleted,
        "runs_deleted": runs_deleted,
        "timelines_deleted": timelines_deleted,
        "alerts_deleted": alerts_deleted,
    }
