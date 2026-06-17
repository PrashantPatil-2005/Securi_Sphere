from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services import siem_analytics as analytics
from app.utils.query import ListParams, resolve_time_range

router = APIRouter(prefix="/siem", tags=["siem"])


def _host_id(host_id: str | None = None) -> UUID | None:
    return UUID(host_id) if host_id else None


@router.get("/events-trend")
async def events_trend(
    preset: str | None = ListParams.preset(),
    from_time: datetime | None = ListParams.from_time(),
    to_time: datetime | None = ListParams.to_time(),
    host_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tr = resolve_time_range(preset, from_time, to_time)
    return await analytics.events_trend(db, tr, _host_id(host_id))


@router.get("/failed-logins")
async def failed_logins(
    preset: str | None = ListParams.preset(),
    from_time: datetime | None = ListParams.from_time(),
    to_time: datetime | None = ListParams.to_time(),
    host_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tr = resolve_time_range(preset, from_time, to_time)
    return await analytics.failed_login_analytics(db, tr, _host_id(host_id))


@router.get("/severity-distribution")
async def severity_distribution(
    preset: str | None = ListParams.preset(),
    from_time: datetime | None = ListParams.from_time(),
    to_time: datetime | None = ListParams.to_time(),
    host_id: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tr = resolve_time_range(preset, from_time, to_time)
    return await analytics.severity_distribution(db, tr, _host_id(host_id), status)


@router.get("/event-types")
async def event_types(
    preset: str | None = ListParams.preset(),
    from_time: datetime | None = ListParams.from_time(),
    to_time: datetime | None = ListParams.to_time(),
    host_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tr = resolve_time_range(preset, from_time, to_time)
    return await analytics.event_type_distribution(db, tr, _host_id(host_id))


@router.get("/top-risky-hosts")
async def top_risky_hosts(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await analytics.top_risky_hosts(db, limit)


@router.get("/host-risk")
async def host_risk(
    preset: str | None = ListParams.preset(),
    from_time: datetime | None = ListParams.from_time(),
    to_time: datetime | None = ListParams.to_time(),
    host_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tr = resolve_time_range(preset, from_time, to_time)
    return await analytics.host_risk_dashboard(db, tr, _host_id(host_id))


@router.get("/host-health")
async def host_health(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await analytics.host_health_monitoring(db)


@router.get("/executive")
async def executive(
    preset: str | None = ListParams.preset(),
    from_time: datetime | None = ListParams.from_time(),
    to_time: datetime | None = ListParams.to_time(),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tr = resolve_time_range(preset, from_time, to_time)
    return await analytics.executive_summary(db, tr)


@router.get("/mitre")
async def mitre_stats(
    preset: str | None = ListParams.preset(),
    from_time: datetime | None = ListParams.from_time(),
    to_time: datetime | None = ListParams.to_time(),
    host_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tr = resolve_time_range(preset, from_time, to_time)
    return await analytics.mitre_stats(db, tr, _host_id(host_id))


@router.get("/historical")
async def historical(
    view: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await analytics.historical_analytics(db, view)


@router.get("/attack-timelines")
async def attack_timelines(
    preset: str | None = ListParams.preset(),
    from_time: datetime | None = ListParams.from_time(),
    to_time: datetime | None = ListParams.to_time(),
    host_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tr = resolve_time_range(preset, from_time, to_time)
    return await analytics.attack_timeline_list(db, tr, _host_id(host_id))
