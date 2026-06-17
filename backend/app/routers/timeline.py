from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.event import Event
from app.models.timeline import AttackTimeline
from app.models.user import User
from app.services.timeline import get_timelines
from app.utils.query import ListParams, apply_time_range, resolve_time_range

router = APIRouter(prefix="/timelines", tags=["timelines"])


class TimelineResponse(BaseModel):
    id: UUID
    host_id: UUID
    title: str
    description: str | None
    started_at: datetime
    ended_at: datetime
    event_ids: list
    mitre_techniques: list
    severity: str
    confidence: float
    status: str
    model_config = {"from_attributes": True}


class EventResponse(BaseModel):
    id: UUID
    event_type: str
    severity: str
    description: str | None
    mitre_technique_id: str | None
    timestamp: datetime
    model_config = {"from_attributes": True}


@router.get("", response_model=list[TimelineResponse])
async def list_timelines(
    host_id: UUID | None = None,
    preset: str | None = ListParams.preset(),
    from_time: datetime | None = ListParams.from_time(),
    to_time: datetime | None = ListParams.to_time(),
    page: int = ListParams.page(),
    page_size: int = ListParams.page_size(),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    tr = resolve_time_range(preset, from_time, to_time)
    q = select(AttackTimeline).order_by(AttackTimeline.started_at.desc())
    if host_id:
        q = q.where(AttackTimeline.host_id == host_id)
    for clause in apply_time_range(AttackTimeline.started_at, tr):
        q = q.where(clause)
    result = await db.execute(q.offset((page - 1) * page_size).limit(page_size))
    return list(result.scalars().all())


@router.get("/{timeline_id}/events", response_model=list[EventResponse])
async def timeline_events(timeline_id: UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await db.execute(select(AttackTimeline).where(AttackTimeline.id == timeline_id))
    tl = result.scalar_one_or_none()
    if not tl or not tl.event_ids:
        return []
    ids = [UUID(i) for i in tl.event_ids]
    events = (await db.execute(select(Event).where(Event.id.in_(ids)).order_by(Event.timestamp))).scalars().all()
    return list(events)
