from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import cast, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import String

from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models.alert import Alert
from app.models.event import Event
from app.models.host import Host
from app.models.user import User
from app.config import settings
from app.schemas.assistant import NLSearchRequest, NLSearchResponse
from app.services.ai.nl_search import nl_to_siem_query
from app.utils.query import resolve_time_range

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
async def global_search(
    q: str = Query(..., min_length=1),
    exact: bool = False,
    preset: str | None = Query(None),
    from_time: datetime | None = Query(None, alias="from"),
    to_time: datetime | None = Query(None, alias="to"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tr = resolve_time_range(preset, from_time, to_time)

    os_from = tr.from_time.isoformat() if tr.from_time else None
    os_to = tr.to_time.isoformat() if tr.to_time else None
    from app.search.opensearch_client import global_search_opensearch

    os_result = await global_search_opensearch(
        q, exact=exact, from_time=os_from, to_time=os_to, limit=20
    )
    if os_result is not None:
        users: list[User] = []
        user_with_role = (
            await db.execute(select(User).options(selectinload(User.role)).where(User.id == user.id))
        ).scalar_one()
        if user_with_role.role and user_with_role.role.name == "admin":
            uq = select(User).limit(20)
            if exact:
                uq = uq.where(User.email == q)
            else:
                uq = uq.where(or_(User.email.ilike(f"%{q}%"), User.full_name.ilike(f"%{q}%")))
            users = list((await db.execute(uq)).scalars().all())
        return {
            "query": q,
            "exact": exact,
            "backend": "opensearch",
            "hosts": os_result["hosts"],
            "alerts": os_result["alerts"],
            "events": os_result["events"],
            "users": [{"id": str(u.id), "email": u.email, "full_name": u.full_name} for u in users],
        }

    pattern = q if exact else f"%{q}%"

    host_q = select(Host).limit(20)
    if exact:
        host_q = host_q.where(or_(Host.name == q, Host.hostname == q, cast(Host.ip_address, String) == q))
    else:
        host_q = host_q.where(
            or_(Host.name.ilike(pattern), Host.hostname.ilike(pattern), cast(Host.ip_address, String).ilike(pattern))
        )
    hosts = list((await db.execute(host_q)).scalars().all())

    alert_q = select(Alert)
    if tr.from_time:
        alert_q = alert_q.where(Alert.created_at >= tr.from_time)
    if tr.to_time:
        alert_q = alert_q.where(Alert.created_at <= tr.to_time)
    if exact:
        alert_q = alert_q.where(or_(Alert.title == q, Alert.description == q))
    else:
        alert_q = alert_q.where(or_(Alert.title.ilike(pattern), Alert.description.ilike(pattern)))
    alerts = list((await db.execute(alert_q.limit(20))).scalars().all())

    event_q = select(Event)
    if tr.from_time:
        event_q = event_q.where(Event.timestamp >= tr.from_time)
    if tr.to_time:
        event_q = event_q.where(Event.timestamp <= tr.to_time)
    if exact:
        event_q = event_q.where(or_(Event.description == q, Event.event_type == q, Event.raw_log == q))
    else:
        event_q = event_q.where(
            or_(Event.description.ilike(pattern), Event.event_type.ilike(pattern), Event.raw_log.ilike(pattern))
        )
    events = list((await db.execute(event_q.order_by(Event.timestamp.desc()).limit(20))).scalars().all())

    users: list[User] = []
    user_with_role = (
        await db.execute(select(User).options(selectinload(User.role)).where(User.id == user.id))
    ).scalar_one()
    if user_with_role.role and user_with_role.role.name == "admin":
        uq = select(User).limit(20)
        if exact:
            uq = uq.where(User.email == q)
        else:
            uq = uq.where(or_(User.email.ilike(pattern), User.full_name.ilike(pattern)))
        users = list((await db.execute(uq)).scalars().all())

    return {
        "query": q,
        "exact": exact,
        "backend": "postgres",
        "hosts": [{"id": str(h.id), "name": h.name, "hostname": h.hostname, "status": h.status, "ip": str(h.ip_address) if h.ip_address else None} for h in hosts],
        "alerts": [{"id": str(a.id), "title": a.title, "severity": a.severity, "status": a.status} for a in alerts],
        "events": [{"id": str(e.id), "event_type": e.event_type, "description": e.description, "severity": e.severity} for e in events],
        "users": [{"id": str(u.id), "email": u.email, "full_name": u.full_name} for u in users],
    }


@router.post("/nl", response_model=NLSearchResponse)
async def nl_search(
    body: NLSearchRequest,
    user: User = Depends(get_current_user),
):
    if not settings.ai_assistant_enabled:
        raise HTTPException(status_code=503, detail="AI assistant is disabled")
    result = await nl_to_siem_query(body.query)
    return NLSearchResponse(**result)


@router.get("/siem")
async def siem_search(
    q: str = Query(..., min_length=1),
    preset: str | None = Query(None),
    from_time: datetime | None = Query(None, alias="from"),
    to_time: datetime | None = Query(None, alias="to"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.services.siem_search import execute_siem_search
    return await execute_siem_search(db, q, preset, from_time, to_time, limit)
