from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.user import User
from app.schemas.event import EventListResponse, EventResponse
from app.services.export_service import export_csv, export_json, export_pdf
from app.services.query_builders import query_events
from app.utils.query import ListParams, SortOrder, resolve_time_range

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=EventListResponse)
async def list_events(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    host_id: UUID | None = None,
    severity: str | None = None,
    event_type: str | None = None,
    username: str | None = None,
    source_ip: str | None = None,
    service_name: str | None = None,
    status: str | None = None,
    q: str | None = None,
    exact: bool = False,
    preset: str | None = ListParams.preset(),
    from_time: datetime | None = ListParams.from_time(),
    to_time: datetime | None = ListParams.to_time(),
    sort: SortOrder = ListParams.sort(),
    page: int = ListParams.page(),
    page_size: int = ListParams.page_size(),
    include_simulated: bool | None = Query(None),
):
    tr = resolve_time_range(preset, from_time, to_time)
    items, total = await query_events(
        db, tr,
        host_id=host_id, severity=severity, event_type=event_type,
        username=username, source_ip=source_ip, service_name=service_name, status=status,
        q=q, exact=exact, sort=sort, page=page, page_size=page_size,
        include_simulated=include_simulated,
    )
    return EventListResponse(
        items=[EventResponse.model_validate(e) for e in items],
        total=total, page=page, page_size=page_size,
    )


@router.get("/types")
async def list_event_types(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    from sqlalchemy import select, func
    from app.models.event import Event
    result = await db.execute(select(Event.event_type, func.count()).group_by(Event.event_type).order_by(Event.event_type))
    return [{"event_type": r[0], "count": r[1]} for r in result.all()]


@router.get("/export")
async def export_events(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst")),
    format: str = Query("csv", pattern="^(csv|json|pdf)$"),
    host_id: UUID | None = None,
    severity: str | None = None,
    event_type: str | None = None,
    username: str | None = None,
    source_ip: str | None = None,
    service_name: str | None = None,
    status: str | None = None,
    q: str | None = None,
    preset: str | None = ListParams.preset(),
    from_time: datetime | None = ListParams.from_time(),
    to_time: datetime | None = ListParams.to_time(),
    sort: SortOrder = ListParams.sort(),
    page_size: int = Query(500, ge=1, le=500),
):
    tr = resolve_time_range(preset, from_time, to_time)
    items, _ = await query_events(
        db, tr,
        host_id=host_id, severity=severity, event_type=event_type,
        username=username, source_ip=source_ip, service_name=service_name, status=status,
        q=q, sort=sort, page=1, page_size=page_size,
    )
    rows = [
        {
            "id": str(e.id), "host_id": str(e.host_id), "event_type": e.event_type,
            "severity": e.severity, "description": e.description, "source": e.source,
            "timestamp": str(e.timestamp),
        }
        for e in items
    ]
    if format == "json":
        return export_json(rows, "events.json")
    if format == "pdf":
        return export_pdf(rows, "SecuriSphere Events Export", "events.pdf")
    return export_csv(rows, "events.csv")
