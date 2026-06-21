from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.host import Host
from app.models.siem import Offense, OffenseEvent
from app.models.user import User
from app.utils.query import ListParams, resolve_time_range

router = APIRouter(prefix="/offenses", tags=["offenses"])


class OffenseStatusUpdate(BaseModel):
    status: str


@router.get("")
async def list_offenses(
    status: str | None = None,
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
    q = select(Offense).options(selectinload(Offense.links))
    if status:
        q = q.where(Offense.status == status)
    if host_id:
        q = q.where(Offense.host_id == host_id)
    if tr.from_time:
        q = q.where(Offense.created_at >= tr.from_time)
    if tr.to_time:
        q = q.where(Offense.created_at <= tr.to_time)

    all_rows = list((await db.execute(q.order_by(Offense.updated_at.desc()))).scalars().all())
    hosts = {h.id: h.name for h in (await db.execute(select(Host))).scalars().all()}
    offset = (page - 1) * page_size
    page_rows = all_rows[offset : offset + page_size]

    return {
        "items": [
            {
                "id": str(o.id),
                "offense_number": o.offense_number,
                "host_id": str(o.host_id),
                "host_name": hosts.get(o.host_id, "?"),
                "title": o.title,
                "description": o.description,
                "risk_level": o.risk_level,
                "status": o.status,
                "event_count": o.event_count,
                "created_at": o.created_at.isoformat(),
                "updated_at": o.updated_at.isoformat(),
            }
            for o in page_rows
        ],
        "total": len(all_rows),
        "page": page,
        "page_size": page_size,
    }


@router.get("/{offense_id}")
async def get_offense(
    offense_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    offense = (
        await db.execute(
            select(Offense).options(selectinload(Offense.links)).where(Offense.id == offense_id)
        )
    ).scalar_one_or_none()
    if not offense:
        from fastapi import HTTPException
        raise HTTPException(404, "Offense not found")

    host = (await db.execute(select(Host).where(Host.id == offense.host_id))).scalar_one_or_none()
    from app.models.alert import Alert
    from app.models.event import Event

    events = []
    alerts = []
    for link in offense.links:
        if link.event_id:
            ev = (await db.execute(select(Event).where(Event.id == link.event_id))).scalar_one_or_none()
            if ev:
                events.append({
                    "id": str(ev.id),
                    "event_type": ev.event_type,
                    "description": ev.description,
                    "severity": ev.severity,
                    "timestamp": ev.timestamp.isoformat(),
                })
        if link.alert_id:
            al = (await db.execute(select(Alert).where(Alert.id == link.alert_id))).scalar_one_or_none()
            if al:
                alerts.append({
                    "id": str(al.id),
                    "title": al.title,
                    "severity": al.severity,
                    "status": al.status,
                    "created_at": al.created_at.isoformat(),
                })

    return {
        "id": str(offense.id),
        "offense_number": offense.offense_number,
        "host_id": str(offense.host_id),
        "host_name": host.name if host else "?",
        "title": offense.title,
        "description": offense.description,
        "risk_level": offense.risk_level,
        "status": offense.status,
        "event_count": offense.event_count,
        "events": events,
        "alerts": alerts,
        "created_at": offense.created_at.isoformat(),
        "updated_at": offense.updated_at.isoformat(),
    }


@router.patch("/{offense_id}/status")
async def update_offense_status(
    offense_id: UUID,
    body: OffenseStatusUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst")),
):
    from datetime import timezone
    from fastapi import HTTPException

    if body.status not in ("open", "investigating", "resolved"):
        raise HTTPException(400, "Invalid status")

    offense = (await db.execute(select(Offense).where(Offense.id == offense_id))).scalar_one_or_none()
    if not offense:
        raise HTTPException(404, "Offense not found")

    offense.status = body.status
    offense.updated_at = datetime.now(timezone.utc)
    if body.status == "resolved":
        offense.closed_at = datetime.now(timezone.utc)
    await db.commit()
    return {"id": str(offense.id), "status": offense.status}
