from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.event import Event
from app.models.user import User
from app.schemas.event import EventListResponse, EventResponse

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=EventListResponse)
async def list_events(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    host_id: UUID | None = None,
    severity: str | None = None,
    event_type: str | None = None,
    from_time: datetime | None = Query(None, alias="from"),
    to_time: datetime | None = Query(None, alias="to"),
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    query = select(Event)
    count_query = select(func.count()).select_from(Event)

    if host_id:
        query = query.where(Event.host_id == host_id)
        count_query = count_query.where(Event.host_id == host_id)
    if severity:
        query = query.where(Event.severity == severity)
        count_query = count_query.where(Event.severity == severity)
    if event_type:
        query = query.where(Event.event_type == event_type)
        count_query = count_query.where(Event.event_type == event_type)
    if from_time:
        query = query.where(Event.timestamp >= from_time)
        count_query = count_query.where(Event.timestamp >= from_time)
    if to_time:
        query = query.where(Event.timestamp <= to_time)
        count_query = count_query.where(Event.timestamp <= to_time)
    if q:
        pattern = f"%{q}%"
        query = query.where(Event.description.ilike(pattern) | Event.raw_log.ilike(pattern))
        count_query = count_query.where(Event.description.ilike(pattern) | Event.raw_log.ilike(pattern))

    total = (await db.execute(count_query)).scalar_one()
    result = await db.execute(
        query.order_by(Event.timestamp.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    items = list(result.scalars().all())
    return EventListResponse(items=items, total=total, page=page, page_size=page_size)
