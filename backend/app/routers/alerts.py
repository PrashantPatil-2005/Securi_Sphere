from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.alert import Alert
from app.models.alert_rule import AlertRule
from app.models.event import Event
from app.models.host import Host
from app.models.threat_score import HostThreatScore
from app.models.timeline import AttackTimeline
from app.models.user import User
from app.schemas.alert import (
    AlertInvestigationHost,
    AlertInvestigationResponse,
    AlertInvestigationTimeline,
    AlertListResponse,
    AlertResponse,
    AlertStatusUpdate,
)
from app.schemas.event import EventResponse
from app.services.audit import log_audit
from app.services.detection import update_host_statuses
from app.services.export_service import export_csv, export_json, export_pdf
from app.services.query_builders import query_alerts
from app.utils.query import ListParams, SortOrder, resolve_time_range
from app.websocket.manager import ws_manager

router = APIRouter(prefix="/alerts", tags=["alerts"])

VALID_STATUSES = {"open", "investigating", "resolved", "closed"}


def _to_response(alert: Alert) -> AlertResponse:
    return AlertResponse.model_validate(alert)


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    host_id: UUID | None = None,
    severity: str | None = None,
    status: str | None = None,
    rule_name: str | None = None,
    assigned_to: UUID | None = None,
    q: str | None = None,
    exact: bool = False,
    preset: str | None = ListParams.preset(),
    from_time: datetime | None = ListParams.from_time(),
    to_time: datetime | None = ListParams.to_time(),
    sort: SortOrder = ListParams.sort(),
    page: int = ListParams.page(),
    page_size: int = ListParams.page_size(),
):
    tr = resolve_time_range(preset, from_time, to_time)
    items, total = await query_alerts(
        db, tr,
        host_id=host_id, severity=severity, status=status, rule_name=rule_name,
        assigned_to=assigned_to, q=q, exact=exact, sort=sort, page=page, page_size=page_size,
    )
    return AlertListResponse(items=[_to_response(a) for a in items], total=total, page=page, page_size=page_size)


@router.get("/export")
async def export_alerts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst")),
    format: str = Query("csv", pattern="^(csv|json|pdf)$"),
    host_id: UUID | None = None,
    severity: str | None = None,
    status: str | None = None,
    rule_name: str | None = None,
    assigned_to: UUID | None = None,
    q: str | None = None,
    preset: str | None = ListParams.preset(),
    from_time: datetime | None = ListParams.from_time(),
    to_time: datetime | None = ListParams.to_time(),
    sort: SortOrder = ListParams.sort(),
    page_size: int = Query(500, ge=1, le=500),
):
    tr = resolve_time_range(preset, from_time, to_time)
    items, _ = await query_alerts(
        db, tr,
        host_id=host_id, severity=severity, status=status, rule_name=rule_name,
        assigned_to=assigned_to, q=q, sort=sort, page=1, page_size=page_size,
    )
    rows = [
        {
            "id": str(a.id), "host_id": str(a.host_id), "title": a.title,
            "severity": a.severity, "status": a.status, "confidence": a.confidence,
            "created_at": str(a.created_at), "resolved_at": str(a.resolved_at),
        }
        for a in items
    ]
    if format == "json":
        return export_json(rows, "alerts.json")
    if format == "pdf":
        return export_pdf(rows, "SecuriSphere Alerts Export", "alerts.pdf")
    return export_csv(rows, "alerts.csv")


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return _to_response(alert)


@router.get("/{alert_id}/investigation", response_model=AlertInvestigationResponse)
async def get_alert_investigation(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Alert).options(selectinload(Alert.host)).where(Alert.id == alert_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    host = alert.host
    if not host:
        host = await db.get(Host, alert.host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    score_row = (
        await db.execute(select(HostThreatScore).where(HostThreatScore.host_id == host.id))
    ).scalar_one_or_none()

    window_start = alert.created_at - timedelta(minutes=30)
    window_end = alert.created_at + timedelta(minutes=5)
    events = (
        await db.execute(
            select(Event)
            .where(
                Event.host_id == alert.host_id,
                Event.timestamp >= window_start,
                Event.timestamp <= window_end,
            )
            .order_by(Event.timestamp.desc())
            .limit(25)
        )
    ).scalars().all()

    timelines = (
        await db.execute(
            select(AttackTimeline)
            .where(AttackTimeline.host_id == alert.host_id)
            .order_by(AttackTimeline.started_at.desc())
            .limit(5)
        )
    ).scalars().all()

    return AlertInvestigationResponse(
        alert=_to_response(alert),
        host=AlertInvestigationHost(
            id=host.id,
            name=host.name,
            hostname=host.hostname,
            status=host.status,
            ip_address=str(host.ip_address) if host.ip_address else None,
            risk_score=int(score_row.score) if score_row else None,
        ),
        events=[EventResponse.model_validate(e) for e in events],
        timelines=[
            AlertInvestigationTimeline(
                id=tl.id,
                title=tl.title,
                severity=tl.severity,
                confidence=tl.confidence,
                started_at=tl.started_at,
                status=tl.status,
            )
            for tl in timelines
        ],
    )


@router.patch("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst")),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = "resolved"
    alert.resolved_at = datetime.now(timezone.utc)
    alert.resolved_by = user.id
    await update_host_statuses(db)
    await log_audit(db, "alert_resolve", user_id=user.id, resource_type="alert", resource_id=alert_id)
    await ws_manager.broadcast({"type": "alert_resolved", "data": {"id": str(alert.id)}})
    return _to_response(alert)


@router.patch("/{alert_id}/status", response_model=AlertResponse)
async def update_alert_status(
    alert_id: UUID,
    body: AlertStatusUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst")),
):
    if body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Status must be one of {VALID_STATUSES}")
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = body.status
    if body.assigned_to is not None:
        alert.assigned_to = body.assigned_to
    if body.status in ("resolved", "closed"):
        alert.resolved_at = datetime.now(timezone.utc)
        alert.resolved_by = user.id
    await update_host_statuses(db)
    await log_audit(db, "alert_status_update", user_id=user.id, resource_type="alert", resource_id=alert_id, details={"status": body.status})
    return _to_response(alert)
