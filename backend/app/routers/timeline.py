from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.event import Event
from app.models.timeline import AttackTimeline
from app.models.user import User
from app.schemas.timeline import TimelineResponse, TimelineEventResponse
from app.utils.query import ListParams, apply_time_range, resolve_time_range

router = APIRouter(prefix="/timelines", tags=["timelines"])


@router.get("", response_model=list[TimelineResponse])
async def list_timelines(
    host_id: UUID | None = None,
    preset: str | None = ListParams.preset(),
    from_time: datetime | None = ListParams.from_time(),
    to_time: datetime | None = ListParams.to_time(),
    page: int = ListParams.page(),
    page_size: int = ListParams.page_size(),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tr = resolve_time_range(preset, from_time, to_time)
    q = select(AttackTimeline).order_by(AttackTimeline.started_at.desc())
    if host_id:
        q = q.where(AttackTimeline.host_id == host_id)
    for clause in apply_time_range(AttackTimeline.started_at, tr):
        q = q.where(clause)
    result = await db.execute(q.offset((page - 1) * page_size).limit(page_size))
    return list(result.scalars().all())


@router.get("/{timeline_id}/events", response_model=list[TimelineEventResponse])
async def timeline_events(timeline_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(AttackTimeline).where(AttackTimeline.id == timeline_id))
    tl = result.scalar_one_or_none()
    if not tl or not tl.event_ids:
        return []
    valid_ids = []
    for eid in tl.event_ids:
        try:
            valid_ids.append(UUID(eid))
        except (ValueError, TypeError):
            continue
    if not valid_ids:
        return []
    events = (await db.execute(select(Event).where(Event.id.in_(valid_ids)).order_by(Event.timestamp))).scalars().all()
    return list(events)
