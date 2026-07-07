"""Build unified investigation workspace payloads."""

from datetime import timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.alert import Alert
from app.models.event import Event
from app.models.host import Host
from app.models.incident import Incident, IncidentAlert
from app.models.siem import Offense, OffenseEvent
from app.models.threat_score import HostThreatScore
from app.models.timeline import AttackTimeline
from app.schemas.alert import (
    AlertInvestigationHost,
    AlertInvestigationTimeline,
    AlertResponse,
)
from app.schemas.event import EventResponse
from app.schemas.investigation import (
    InvestigationWorkspaceResponse,
    WorkspaceAnchor,
    WorkspaceIncidentSummary,
    WorkspaceOffenseSummary,
)


def _alert_response(alert: Alert) -> AlertResponse:
    return AlertResponse.model_validate(alert)


async def _host_context(db: AsyncSession, host: Host) -> AlertInvestigationHost:
    score_row = (
        await db.execute(select(HostThreatScore).where(HostThreatScore.host_id == host.id))
    ).scalar_one_or_none()
    return AlertInvestigationHost(
        id=host.id,
        name=host.name,
        hostname=host.hostname,
        status=host.status,
        ip_address=str(host.ip_address) if host.ip_address else None,
        risk_score=int(score_row.score) if score_row else None,
    )


async def _events_near(
    db: AsyncSession,
    host_id: UUID,
    center,
    *,
    minutes_before: int = 30,
    minutes_after: int = 5,
    limit: int = 25,
) -> list[EventResponse]:
    rows = (
        await db.execute(
            select(Event)
            .where(
                Event.host_id == host_id,
                Event.timestamp >= center - timedelta(minutes=minutes_before),
                Event.timestamp <= center + timedelta(minutes=minutes_after),
            )
            .order_by(Event.timestamp.desc())
            .limit(limit)
        )
    ).scalars().all()
    return [EventResponse.model_validate(e) for e in rows]


async def _timelines_for_host(db: AsyncSession, host_id: UUID, limit: int = 5) -> list[AlertInvestigationTimeline]:
    rows = (
        await db.execute(
            select(AttackTimeline)
            .where(AttackTimeline.host_id == host_id)
            .order_by(AttackTimeline.started_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return [
        AlertInvestigationTimeline(
            id=tl.id,
            title=tl.title,
            severity=tl.severity,
            confidence=tl.confidence,
            started_at=tl.started_at,
            status=tl.status,
        )
        for tl in rows
    ]


async def _offense_summary(db: AsyncSession, offense: Offense) -> WorkspaceOffenseSummary:
    host = await db.get(Host, offense.host_id)
    events = []
    alerts = []
    for link in offense.links:
        if link.event_id:
            ev = await db.get(Event, link.event_id)
            if ev:
                events.append({
                    "id": str(ev.id),
                    "event_type": ev.event_type,
                    "description": ev.description,
                    "severity": ev.severity,
                    "timestamp": ev.timestamp.isoformat(),
                })
        if link.alert_id:
            al = await db.get(Alert, link.alert_id)
            if al:
                alerts.append({
                    "id": str(al.id),
                    "title": al.title,
                    "severity": al.severity,
                    "status": al.status,
                    "created_at": al.created_at.isoformat(),
                })
    return WorkspaceOffenseSummary(
        id=offense.id,
        offense_number=offense.offense_number,
        host_id=offense.host_id,
        host_name=host.name if host else None,
        title=offense.title,
        description=offense.description,
        risk_level=offense.risk_level,
        status=offense.status,
        event_count=offense.event_count,
        alert_count=offense.alert_count,
        incident_id=offense.incident_id,
        timeline=offense.timeline or [],
        related_users=offense.related_users or [],
        alerts=alerts,
        events=events,
    )


async def _load_offense(db: AsyncSession, offense_id: UUID) -> Offense:
    offense = (
        await db.execute(
            select(Offense).options(selectinload(Offense.links)).where(Offense.id == offense_id)
        )
    ).scalar_one_or_none()
    if not offense:
        raise HTTPException(status_code=404, detail="Offense not found")
    return offense


async def _incident_summary(db: AsyncSession, incident: Incident) -> WorkspaceIncidentSummary:
    return WorkspaceIncidentSummary(
        id=incident.id,
        title=incident.title,
        description=incident.description,
        severity=incident.severity,
        status=incident.status,
        host_id=incident.host_id,
        created_at=incident.created_at,
        resolved_at=incident.resolved_at,
        notes=[
            {
                "id": str(n.id),
                "content": n.content,
                "user_id": str(n.user_id),
                "created_at": n.created_at.isoformat(),
            }
            for n in incident.notes
        ],
        alert_ids=[str(l.alert_id) for l in incident.alert_links],
    )


async def _load_incident(db: AsyncSession, incident_id: UUID) -> Incident:
    incident = (
        await db.execute(
            select(Incident)
            .options(selectinload(Incident.notes), selectinload(Incident.alert_links))
            .where(Incident.id == incident_id)
        )
    ).scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


async def _offense_for_alert(db: AsyncSession, alert_id: UUID) -> Offense | None:
    link = (
        await db.execute(
            select(OffenseEvent)
            .where(OffenseEvent.alert_id == alert_id)
            .order_by(OffenseEvent.linked_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if not link:
        return None
    return await _load_offense(db, link.offense_id)


async def _offense_for_incident(db: AsyncSession, incident_id: UUID) -> Offense | None:
    return (
        await db.execute(
            select(Offense).where(Offense.incident_id == incident_id).limit(1)
        )
    ).scalar_one_or_none()


async def _alerts_by_ids(db: AsyncSession, alert_ids: list[UUID]) -> list[AlertResponse]:
    if not alert_ids:
        return []
    rows = (await db.execute(select(Alert).where(Alert.id.in_(alert_ids)))).scalars().all()
    return [_alert_response(a) for a in rows]


async def build_workspace_from_alert(db: AsyncSession, alert_id: UUID) -> InvestigationWorkspaceResponse:
    alert = (
        await db.execute(select(Alert).options(selectinload(Alert.host)).where(Alert.id == alert_id))
    ).scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    host = alert.host or await db.get(Host, alert.host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    offense_row = await _offense_for_alert(db, alert_id)
    offense = await _offense_summary(db, offense_row) if offense_row else None

    incident = None
    if offense and offense.incident_id:
        inc = await _load_incident(db, offense.incident_id)
        incident = await _incident_summary(db, inc)
    elif offense_row and offense_row.incident_id:
        inc = await _load_incident(db, offense_row.incident_id)
        incident = await _incident_summary(db, inc)

    linked = await _alerts_by_ids(db, [UUID(aid) for aid in (incident.alert_ids if incident else [])])

    return InvestigationWorkspaceResponse(
        anchor=WorkspaceAnchor(type="alert", id=alert_id),
        alert=_alert_response(alert),
        offense=offense,
        incident=incident,
        host=await _host_context(db, host),
        events=await _events_near(db, host.id, alert.created_at),
        timelines=await _timelines_for_host(db, host.id),
        linked_alerts=linked or [_alert_response(alert)],
    )


async def build_workspace_from_offense(db: AsyncSession, offense_id: UUID) -> InvestigationWorkspaceResponse:
    offense_row = await _load_offense(db, offense_id)
    offense = await _offense_summary(db, offense_row)
    host = await db.get(Host, offense_row.host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    primary_alert = None
    alert_ids = [UUID(a["id"]) for a in offense.alerts if a.get("id")]
    if alert_ids:
        primary_alert = (await db.execute(select(Alert).where(Alert.id == alert_ids[0]))).scalar_one_or_none()

    incident = None
    if offense_row.incident_id:
        inc = await _load_incident(db, offense_row.incident_id)
        incident = await _incident_summary(db, inc)

    center = offense_row.updated_at or offense_row.created_at
    events = await _events_near(db, host.id, center)
    if offense.events and not events:
        event_ids = [UUID(e["id"]) for e in offense.events if e.get("id")]
        if event_ids:
            rows = (await db.execute(select(Event).where(Event.id.in_(event_ids)))).scalars().all()
            events = [EventResponse.model_validate(e) for e in rows]

    linked = await _alerts_by_ids(db, alert_ids)

    return InvestigationWorkspaceResponse(
        anchor=WorkspaceAnchor(type="offense", id=offense_id),
        alert=_alert_response(primary_alert) if primary_alert else None,
        offense=offense,
        incident=incident,
        host=await _host_context(db, host),
        events=events,
        timelines=await _timelines_for_host(db, host.id),
        linked_alerts=linked,
    )


async def build_workspace_from_incident(db: AsyncSession, incident_id: UUID) -> InvestigationWorkspaceResponse:
    incident_row = await _load_incident(db, incident_id)
    incident = await _incident_summary(db, incident_row)

    offense_row = await _offense_for_incident(db, incident_id)
    offense = await _offense_summary(db, offense_row) if offense_row else None

    host = None
    host_ctx = None
    if incident_row.host_id:
        host = await db.get(Host, incident_row.host_id)
    elif offense_row:
        host = await db.get(Host, offense_row.host_id)
    if host:
        host_ctx = await _host_context(db, host)

    alert_ids = [UUID(aid) for aid in incident.alert_ids]
    linked = await _alerts_by_ids(db, alert_ids)
    primary_alert = linked[0] if linked else None

    events: list[EventResponse] = []
    timelines: list[AlertInvestigationTimeline] = []
    if host:
        center = incident_row.created_at
        if primary_alert:
            center = primary_alert.created_at
        events = await _events_near(db, host.id, center)
        timelines = await _timelines_for_host(db, host.id)

    return InvestigationWorkspaceResponse(
        anchor=WorkspaceAnchor(type="incident", id=incident_id),
        alert=primary_alert,
        offense=offense,
        incident=incident,
        host=host_ctx,
        events=events,
        timelines=timelines,
        linked_alerts=linked,
    )


async def build_investigation_workspace(
    db: AsyncSession,
    *,
    alert_id: UUID | None = None,
    offense_id: UUID | None = None,
    incident_id: UUID | None = None,
) -> InvestigationWorkspaceResponse:
    provided = sum(1 for x in (alert_id, offense_id, incident_id) if x is not None)
    if provided != 1:
        raise HTTPException(
            status_code=400,
            detail="Provide exactly one of alert_id, offense_id, or incident_id",
        )
    if alert_id:
        return await build_workspace_from_alert(db, alert_id)
    if offense_id:
        return await build_workspace_from_offense(db, offense_id)
    return await build_workspace_from_incident(db, incident_id)  # type: ignore[arg-type]
