"""Build unified investigation workspace payloads.

Each related-data section (host context, events, timelines, linked alerts,
offense summary, incident summary) is loaded independently. A failure in one
section degrades that section to an empty value and is reported in
``partial_errors`` — a 200 response does not claim every section loaded.
"""

import logging
from datetime import timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.alert import Alert
from app.models.event import Event
from app.models.host import Host
from app.models.incident import Incident
from app.models.siem import Offense, OffenseEvent
from app.models.threat_score import HostThreatScore
from app.models.timeline import AttackTimeline
from app.models.user import User
from app.schemas.alert import (
    AlertInvestigationHost,
    AlertInvestigationTimeline,
    AlertResponse,
)
from app.schemas.event import EventResponse
from app.schemas.investigation import (
    InvestigationWorkspaceResponse,
    WorkspaceAnchor,
    WorkspaceEntities,
    WorkspaceEntityHost,
    WorkspaceIncidentSummary,
    WorkspaceMitre,
    WorkspaceNote,
    WorkspaceOffenseSummary,
    WorkspaceProvenance,
    WorkspaceTimelineEntry,
)

logger = logging.getLogger(__name__)

TIMELINE_LIMIT = 50
ENTITY_LIMIT = 20


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

    event_ids = [link.event_id for link in offense.links if link.event_id]
    alert_ids = [link.alert_id for link in offense.links if link.alert_id]

    events_map: dict[UUID, Event] = {}
    alerts_map: dict[UUID, Alert] = {}

    if event_ids:
        rows = (await db.execute(select(Event).where(Event.id.in_(event_ids)))).scalars().all()
        events_map = {e.id: e for e in rows}
    if alert_ids:
        rows = (await db.execute(select(Alert).where(Alert.id.in_(alert_ids)))).scalars().all()
        alerts_map = {a.id: a for a in rows}

    events = []
    alerts = []
    for link in offense.links:
        if link.event_id and link.event_id in events_map:
            ev = events_map[link.event_id]
            events.append({
                "id": str(ev.id),
                "event_type": ev.event_type,
                "description": ev.description,
                "severity": ev.severity,
                "timestamp": ev.timestamp.isoformat(),
            })
        if link.alert_id and link.alert_id in alerts_map:
            al = alerts_map[link.alert_id]
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
        created_at=offense.created_at,
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


async def _user_emails(db: AsyncSession, user_ids: list[UUID]) -> dict[UUID, str]:
    unique = [uid for uid in dict.fromkeys(user_ids) if uid]
    if not unique:
        return {}
    rows = (await db.execute(select(User.id, User.email).where(User.id.in_(unique)))).all()
    return {row.id: row.email for row in rows}


async def _incident_summary(db: AsyncSession, incident: Incident) -> WorkspaceIncidentSummary:
    note_user_ids = [n.user_id for n in incident.notes]
    if incident.assigned_to:
        note_user_ids.append(incident.assigned_to)
    emails = await _user_emails(db, note_user_ids)

    return WorkspaceIncidentSummary(
        id=incident.id,
        title=incident.title,
        description=incident.description,
        severity=incident.severity,
        status=incident.status,
        host_id=incident.host_id,
        assigned_to=incident.assigned_to,
        assignee_email=emails.get(incident.assigned_to) if incident.assigned_to else None,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
        resolved_at=incident.resolved_at,
        confidence=float(incident.confidence or 0.0),
        first_observed=incident.first_observed,
        last_observed=incident.last_observed,
        affected_hosts=list(incident.affected_hosts or []),
        affected_users=list(incident.affected_users or []),
        affected_services=list(incident.affected_services or []),
        mitre_technique_ids=list(incident.mitre_technique_ids or []),
        mitre_tactics=list(incident.mitre_tactics or []),
        simulated=bool(incident.simulated),
        source=incident.source,
        notes=[
            WorkspaceNote(
                id=n.id,
                content=n.content,
                user_id=n.user_id,
                user_email=emails.get(n.user_id),
                created_at=n.created_at,
            )
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
    # Offense.links must be eager-loaded: _offense_summary() reads it, and lazy
    # loading is illegal in the asyncio session (raises MissingGreenlet -> 500).
    return (
        await db.execute(
            select(Offense)
            .options(selectinload(Offense.links))
            .where(Offense.incident_id == incident_id)
            .limit(1)
        )
    ).scalar_one_or_none()


async def _alerts_by_ids(db: AsyncSession, alert_ids: list[UUID]) -> list[AlertResponse]:
    if not alert_ids:
        return []
    rows = (await db.execute(select(Alert).where(Alert.id.in_(alert_ids)))).scalars().all()
    return [_alert_response(a) for a in rows]


def _build_investigation_timeline(
    *,
    incident: WorkspaceIncidentSummary | None,
    offense: WorkspaceOffenseSummary | None,
    alert: AlertResponse | None,
    linked_alerts: list[AlertResponse],
    events: list[EventResponse],
) -> list[WorkspaceTimelineEntry]:
    entries: list[WorkspaceTimelineEntry] = []

    if incident:
        entries.append(WorkspaceTimelineEntry(
            type="incident",
            timestamp=incident.created_at,
            title=f"Incident created: {incident.title}",
            description=incident.description,
            severity=incident.severity,
            ref_id=str(incident.id),
            simulated=incident.simulated,
        ))
        if incident.resolved_at:
            entries.append(WorkspaceTimelineEntry(
                type="incident",
                timestamp=incident.resolved_at,
                title=f"Incident {incident.status}: {incident.title}",
                severity=incident.severity,
                ref_id=str(incident.id),
                simulated=incident.simulated,
            ))
        for note in incident.notes:
            entries.append(WorkspaceTimelineEntry(
                type="note",
                timestamp=note.created_at,
                title=f"Note by {note.user_email or note.user_id}",
                description=note.content,
                ref_id=str(note.id),
                simulated=incident.simulated,
            ))

    if offense:
        entries.append(WorkspaceTimelineEntry(
            type="offense",
            timestamp=offense.created_at or (alert.created_at if alert else None) or (events[0].timestamp if events else None),
            title=f"Offense #{offense.offense_number}: {offense.title}",
            description=offense.description,
            severity=offense.risk_level,
            ref_id=str(offense.id),
            simulated=incident.simulated if incident else False,
        ))

    seen_alert_ids: set[str] = set()
    for a in linked_alerts or ([alert] if alert else []):
        if str(a.id) in seen_alert_ids:
            continue
        seen_alert_ids.add(str(a.id))
        entries.append(WorkspaceTimelineEntry(
            type="alert",
            timestamp=a.created_at,
            title=a.title,
            description=a.description,
            severity=a.severity,
            ref_id=str(a.id),
            simulated=(a.source == "simulation"),
        ))

    for e in events:
        entries.append(WorkspaceTimelineEntry(
            type="event",
            timestamp=e.timestamp,
            title=f"{e.event_type}: {e.description or ''}".strip(),
            description=e.raw_log,
            severity=e.severity,
            ref_id=str(e.id),
            simulated=(e.source == "simulation"),
        ))

    entries = [e for e in entries if e.timestamp is not None]
    entries.sort(key=lambda t: t.timestamp, reverse=True)
    return entries[:TIMELINE_LIMIT]


def _build_entities(
    *,
    host: AlertInvestigationHost | None,
    incident: WorkspaceIncidentSummary | None,
    offense: WorkspaceOffenseSummary | None,
    events: list[EventResponse],
) -> WorkspaceEntities:
    hosts: list[WorkspaceEntityHost] = []
    seen_hosts: set[str] = set()

    if host:
        hosts.append(WorkspaceEntityHost(id=host.id, name=host.name, ip=host.ip_address))
        seen_hosts.add(host.name)
    if incident:
        for name in incident.affected_hosts:
            key = str(name)
            if key and key not in seen_hosts:
                hosts.append(WorkspaceEntityHost(name=key))
                seen_hosts.add(key)
    if offense and offense.host_name and offense.host_name not in seen_hosts:
        hosts.append(WorkspaceEntityHost(id=offense.host_id, name=offense.host_name))
        seen_hosts.add(offense.host_name)

    accounts: list[str] = []
    for source_list in (
        (offense.related_users if offense else []),
        (incident.affected_users if incident else []),
    ):
        for acct in source_list:
            key = str(acct)
            if key and key not in accounts:
                accounts.append(key)

    network_ips: list[str] = []
    if host and host.ip_address and host.ip_address not in network_ips:
        network_ips.append(host.ip_address)
    for e in events:
        if e.source_ip and e.source_ip not in network_ips:
            network_ips.append(e.source_ip)

    return WorkspaceEntities(
        hosts=hosts[:ENTITY_LIMIT],
        accounts=accounts[:ENTITY_LIMIT],
        network_ips=network_ips[:ENTITY_LIMIT],
    )


def _build_mitre(
    *,
    incident: WorkspaceIncidentSummary | None,
    alert: AlertResponse | None,
    linked_alerts: list[AlertResponse],
) -> WorkspaceMitre:
    techniques: list[str] = []
    tactics: list[str] = []

    def _add(items: list[str], value: str | None) -> None:
        if value and value not in items:
            items.append(value)

    if incident:
        for t in incident.mitre_technique_ids:
            _add(techniques, str(t))
        for t in incident.mitre_tactics:
            _add(tactics, str(t))
    for a in linked_alerts or ([alert] if alert else []):
        _add(techniques, a.mitre_technique_id)

    return WorkspaceMitre(technique_ids=techniques, tactics=tactics)


def _build_provenance(
    *,
    incident: WorkspaceIncidentSummary | None,
    alert: AlertResponse | None,
    linked_alerts: list[AlertResponse],
    events: list[EventResponse],
) -> WorkspaceProvenance:
    sources: list[str] = []
    simulated = bool(incident and incident.simulated)

    def _add_source(value: str | None) -> None:
        if value and value not in sources:
            sources.append(value)

    if incident:
        _add_source(incident.source)
    for a in linked_alerts or ([alert] if alert else []):
        _add_source(a.source)
        if a.source == "simulation":
            simulated = True
    for e in events:
        _add_source(e.source)
        if e.source == "simulation":
            simulated = True

    return WorkspaceProvenance(simulated=simulated, sources=sources)


async def _try_section(partial_errors: list[str], name: str, factory):
    """Run a related-data section; record honest failure instead of 500ing the case."""
    try:
        return await factory()
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — one broken section must not sink the case
        logger.warning("workspace section %r failed: %s", name, exc)
        partial_errors.append(name)
        return None


async def build_workspace_from_alert(db: AsyncSession, alert_id: UUID) -> InvestigationWorkspaceResponse:
    alert = (
        await db.execute(select(Alert).options(selectinload(Alert.host)).where(Alert.id == alert_id))
    ).scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    host = alert.host or await db.get(Host, alert.host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    partial_errors: list[str] = []

    offense_row = await _try_section(partial_errors, "offense", lambda: _offense_for_alert(db, alert_id))
    offense = await _try_section(partial_errors, "offense", lambda: _offense_summary(db, offense_row)) if offense_row else None

    incident_row: Incident | None = None
    if offense_row and offense_row.incident_id:
        incident_row = await _try_section(partial_errors, "incident", lambda: _load_incident(db, offense_row.incident_id))
    incident = await _try_section(partial_errors, "incident", lambda: _incident_summary(db, incident_row)) if incident_row else None

    linked = await _try_section(
        partial_errors,
        "linked_alerts",
        lambda: _alerts_by_ids(db, [UUID(aid) for aid in (incident.alert_ids if incident else [])]),
    ) or []
    if not linked:
        linked = [_alert_response(alert)]

    host_ctx = await _try_section(partial_errors, "host", lambda: _host_context(db, host))
    events = await _try_section(partial_errors, "events", lambda: _events_near(db, host.id, alert.created_at)) or []
    timelines = await _try_section(partial_errors, "timelines", lambda: _timelines_for_host(db, host.id)) or []

    return _finalize(
        anchor=WorkspaceAnchor(type="alert", id=alert_id),
        alert=_alert_response(alert),
        offense=offense,
        incident=incident,
        host=host_ctx,
        events=events,
        timelines=timelines,
        linked_alerts=linked,
        partial_errors=partial_errors,
    )


async def build_workspace_from_offense(db: AsyncSession, offense_id: UUID) -> InvestigationWorkspaceResponse:
    offense_row = await _load_offense(db, offense_id)
    host = await db.get(Host, offense_row.host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    partial_errors: list[str] = []

    offense = await _try_section(partial_errors, "offense", lambda: _offense_summary(db, offense_row))

    incident_row = None
    if offense_row.incident_id:
        incident_row = await _try_section(partial_errors, "incident", lambda: _load_incident(db, offense_row.incident_id))
    incident = await _try_section(partial_errors, "incident", lambda: _incident_summary(db, incident_row)) if incident_row else None

    primary_alert = None
    alert_ids = [UUID(a["id"]) for a in (offense.alerts if offense else []) if a.get("id")]
    if alert_ids:
        primary_alert = (await db.execute(select(Alert).where(Alert.id == alert_ids[0]))).scalar_one_or_none()

    center = offense_row.updated_at or offense_row.created_at
    events = await _try_section(partial_errors, "events", lambda: _events_near(db, host.id, center)) or []
    if offense and offense.events and not events:
        event_ids = [UUID(e["id"]) for e in offense.events if e.get("id")]
        if event_ids:
            rows = (await db.execute(select(Event).where(Event.id.in_(event_ids)))).scalars().all()
            events = [EventResponse.model_validate(e) for e in rows]

    linked = await _try_section(partial_errors, "linked_alerts", lambda: _alerts_by_ids(db, alert_ids)) or []
    host_ctx = await _try_section(partial_errors, "host", lambda: _host_context(db, host))
    timelines = await _try_section(partial_errors, "timelines", lambda: _timelines_for_host(db, host.id)) or []

    return _finalize(
        anchor=WorkspaceAnchor(type="offense", id=offense_id),
        alert=_alert_response(primary_alert) if primary_alert else None,
        offense=offense,
        incident=incident,
        host=host_ctx,
        events=events,
        timelines=timelines,
        linked_alerts=linked,
        partial_errors=partial_errors,
    )


async def build_workspace_from_incident(db: AsyncSession, incident_id: UUID) -> InvestigationWorkspaceResponse:
    incident_row = await _load_incident(db, incident_id)

    partial_errors: list[str] = []

    incident = await _try_section(partial_errors, "incident", lambda: _incident_summary(db, incident_row))
    offense_row = await _try_section(partial_errors, "offense", lambda: _offense_for_incident(db, incident_id))
    offense = await _try_section(partial_errors, "offense", lambda: _offense_summary(db, offense_row)) if offense_row else None

    host = None
    if incident_row.host_id:
        host = await db.get(Host, incident_row.host_id)
    elif offense_row:
        host = await db.get(Host, offense_row.host_id)
    host_ctx = await _try_section(partial_errors, "host", lambda: _host_context(db, host)) if host else None

    alert_ids = [UUID(aid) for aid in (incident.alert_ids if incident else [])]
    linked = await _try_section(partial_errors, "linked_alerts", lambda: _alerts_by_ids(db, alert_ids)) or []
    primary_alert = linked[0] if linked else None

    events: list[EventResponse] = []
    timelines: list[AlertInvestigationTimeline] = []
    if host:
        center = incident_row.created_at
        if primary_alert:
            center = primary_alert.created_at
        events = await _try_section(partial_errors, "events", lambda: _events_near(db, host.id, center)) or []
        timelines = await _try_section(partial_errors, "timelines", lambda: _timelines_for_host(db, host.id)) or []

    return _finalize(
        anchor=WorkspaceAnchor(type="incident", id=incident_id),
        alert=primary_alert,
        offense=offense,
        incident=incident,
        host=host_ctx,
        events=events,
        timelines=timelines,
        linked_alerts=linked,
        partial_errors=partial_errors,
    )


def _finalize(
    *,
    anchor: WorkspaceAnchor,
    alert: AlertResponse | None,
    offense: WorkspaceOffenseSummary | None,
    incident: WorkspaceIncidentSummary | None,
    host: AlertInvestigationHost | None,
    events: list[EventResponse],
    timelines: list[AlertInvestigationTimeline],
    linked_alerts: list[AlertResponse],
    partial_errors: list[str],
) -> InvestigationWorkspaceResponse:
    investigation_timeline: list[WorkspaceTimelineEntry] = []
    entities = WorkspaceEntities()
    mitre = WorkspaceMitre()
    provenance = WorkspaceProvenance()

    try:
        investigation_timeline = _build_investigation_timeline(
            incident=incident,
            offense=offense,
            alert=alert,
            linked_alerts=linked_alerts,
            events=events,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("workspace timeline merge failed: %s", exc)
        partial_errors.append("investigation_timeline")

    try:
        entities = _build_entities(host=host, incident=incident, offense=offense, events=events)
    except Exception as exc:  # noqa: BLE001
        logger.warning("workspace entities merge failed: %s", exc)
        partial_errors.append("entities")

    try:
        mitre = _build_mitre(incident=incident, alert=alert, linked_alerts=linked_alerts)
    except Exception as exc:  # noqa: BLE001
        logger.warning("workspace mitre merge failed: %s", exc)
        partial_errors.append("mitre")

    try:
        provenance = _build_provenance(
            incident=incident, alert=alert, linked_alerts=linked_alerts, events=events
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("workspace provenance merge failed: %s", exc)
        partial_errors.append("provenance")

    return InvestigationWorkspaceResponse(
        anchor=anchor,
        alert=alert,
        offense=offense,
        incident=incident,
        host=host,
        events=events,
        timelines=timelines,
        linked_alerts=linked_alerts,
        investigation_timeline=investigation_timeline,
        entities=entities,
        mitre=mitre,
        provenance=provenance,
        partial_errors=partial_errors,
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
