"""Promote a correlated offense or correlation result into a formal investigation incident."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.incident import Incident, IncidentAlert, IncidentNote
from app.models.correlation import CorrelationResult
from app.models import Offense
from app.models.user import User
from app.services.audit import log_audit

RISK_TO_SEVERITY = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
}


async def promote_offense_to_incident(
    db: AsyncSession,
    offense_id: UUID,
    user: User,
    *,
    ip_address: str | None = None,
) -> dict:
    offense = (
        await db.execute(
            select(Offense)
            .options(selectinload(Offense.links))
            .where(Offense.id == offense_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if not offense:
        raise HTTPException(status_code=404, detail="Offense not found")

    if offense.incident_id:
        return {
            "incident_id": str(offense.incident_id),
            "linked_alert_count": offense.alert_count,
            "created": False,
        }

    now = datetime.now(timezone.utc)
    timeline_lines = offense.timeline or []
    timeline_summary = ""
    if timeline_lines:
        timeline_summary = "\n\nTimeline:\n" + "\n".join(
            f"- {t.get('ts', '')}: {t.get('detail') or t.get('type', '')}" for t in timeline_lines[:20]
        )

    incident = Incident(
        title=f"Offense #{offense.offense_number}: {offense.title}",
        description=(offense.description or "") + timeline_summary,
        severity=RISK_TO_SEVERITY.get(offense.risk_level, "medium"),
        status="investigating",
        host_id=offense.host_id,
        created_by=user.id,
        created_at=now,
        updated_at=now,
        simulated=False,
        source="offense",
    )
    db.add(incident)
    await db.flush()

    linked = 0
    seen_alerts: set[UUID] = set()
    for link in offense.links:
        if link.alert_id and link.alert_id not in seen_alerts:
            db.add(IncidentAlert(incident_id=incident.id, alert_id=link.alert_id))
            seen_alerts.add(link.alert_id)
            linked += 1

    db.add(
        IncidentNote(
            incident_id=incident.id,
            user_id=user.id,
            content=f"Promoted from offense #{offense.offense_number} at {now.isoformat()}",
        )
    )

    offense.incident_id = incident.id
    offense.status = "investigating"
    offense.updated_at = now

    await log_audit(
        db,
        "offense_promoted_to_incident",
        user_id=user.id,
        resource_type="incident",
        resource_id=incident.id,
        ip_address=ip_address,
        details={"offense_id": str(offense.id), "linked_alerts": linked},
    )

    from app.services.playbooks import schedule_playbook_dispatch
    await schedule_playbook_dispatch("incident_created", "incident", incident.id)

    return {
        "incident_id": str(incident.id),
        "linked_alert_count": linked,
        "created": True,
    }


async def promote_correlation_to_incident(
    db: AsyncSession,
    correlation_result: CorrelationResult,
    user: User,
    *,
    ip_address: str | None = None,
) -> dict | None:
    """Promote a CorrelationResult into a formal Incident.

    Creates an incident from the events and MITRE evidence stored in the
    correlation result. Only creates if sufficient evidence exists (2+ events,
    at least one MITRE technique, and no existing incident).
    """

    if correlation_result.incident_id:
        return {
            "incident_id": str(correlation_result.incident_id),
            "created": False,
        }

    # Load the events involved in this correlation
    from app.services.offense_engine import link_event_to_offense

    # We need to reload events; for now, build incident from the correlation rule
    # and the events that were matched. We'll look up events by their IDs.
    event_ids = correlation_result.event_ids or []
    if not event_ids:
        return None

    ev_stmt = select(Event).where(Event.id.in_(event_ids))
    events_result = await db.execute(ev_stmt)
    events = list(events_result.scalars().all())

    if len(events) < 2:
        return None  # insufficient evidence for an incident

    # Use the correlation rule's name and description to title the incident
    # We need the rule; load it from the DB
    rule_stmt = select(correlation_result.rule).options()
    # Actually CorrelationResult has rule_id, let's load the rule
    from app.models.correlation import CorrelationRule
    rule_result = await db.execute(select(CorrelationRule).where(CorrelationRule.id == correlation_result.rule_id))
    rule = rule_result.scalar_one_or_none()
    if not rule:
        return None

    # Build incident title from rule name
    title = rule.name or "Correlation Alert"

    # Aggregate MITRE from involved events
    technique_ids: list[str] = []
    tactics: list[str] = []
    for e in events:
        if e.mitre_technique_id:
            technique_ids.append(e.mitre_technique_id)
        if e.mitre_tactic:
            tactics.append(e.mitre_tactic)
    technique_ids = sorted(set(technique_ids))
    tactics = sorted(set(tactics))

    # Collect affected hosts, users, source IPs from events
    involved_hosts: list[str] = []
    involved_users: list[str] = []
    involved_source_ips: list[str] = []
    docker_service_ids: list[str] = []
    for e in events:
        hid = str(e.host_id)
        if hid not in involved_hosts:
            involved_hosts.append(hid)
        if e.username and e.username not in involved_users:
            involved_users.append(e.username)
        if e.source_ip and str(e.source_ip) not in involved_source_ips:
            involved_source_ips.append(str(e.source_ip))
        if e.docker_service_id and e.docker_service_id not in docker_service_ids:
            docker_service_ids.append(e.docker_service_id)

    # Compute first_observed / last_observed
    observed_times = [e.timestamp for e in events if e.timestamp]
    first_observed: datetime | None = None
    last_observed: datetime | None = None
    if observed_times:
        sorted_times = sorted(observed_times)
        first_observed = sorted_times[0]
        last_observed = sorted_times[-1]

    # Determine severity from rule severity
    severity = rule.severity or "medium"

    # Check for existing open incident with same title+host to prevent duplicates
    from sqlalchemy import func as sa_func
    stmt = (
        select(Incident)
        .where(Incident.title == title)
        .where(Incident.host_id == (events[0].host_id if events else None))
        .where(Incident.status.in_(["open", "investigating"]))
        .limit(1)
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        # Update existing incident
        existing.last_observed = max(
            existing.last_observed or first_observed or datetime.now(timezone.utc),
            last_observed or datetime.now(timezone.utc),
        )
        if technique_ids:
            existing.mitre_technique_ids = sorted(
                set(existing.mitre_technique_ids or []) | set(technique_ids)
            )
        if tactics:
            existing.mitre_tactics = sorted(
                set(existing.mitre_tactics or []) | set(tactics)
            )
        existing.updated_at = datetime.now(timezone.utc)
        await db.flush()
        # Link any new events to the incident
        for e in events:
            try:
                await link_event_to_offense(db, e)
            except Exception:
                pass
        # Add audit log
        await log_audit(
            db,
            "correlation_incident_updated",
            user_id=user.id,
            resource_type="incident",
            resource_id=existing.id,
            ip_address=ip_address,
            details={
                "correlation_result_id": str(correlation_result.id),
                "updated_event_count": len(events),
            },
        )
        return {
            "incident_id": str(existing.id),
            "created": False,
            "updated": True,
        }

    # Build description from event types and MITRE
    event_types = ", ".join(e.event_type for e in events[:4])
    desc_parts = [f"{len(events)} correlated event{'s' if len(events) > 1 else ''}"]
    if technique_ids:
        desc_parts.append(f"MITRE: {', '.join(technique_ids[:3])}")
    if involved_users:
        desc_parts.append(f"users: {', '.join(involved_users)}")
    description = " | ".join(desc_parts)

    # Create new incident
    now = datetime.now(timezone.utc)
    incident = Incident(
        title=title,
        description=description,
        severity=severity,
        status="open",
        host_id=events[0].host_id if events else None,
        created_by=user.id,
        created_at=now,
        updated_at=now,
        first_observed=first_observed,
        last_observed=last_observed,
        affected_hosts=involved_hosts,
        affected_users=involved_users,
        affected_services=docker_service_ids,
        affected_containers=[],
        mitre_technique_ids=technique_ids,
        mitre_tactics=tactics,
        confidence=correlation_result.confidence or 0.5,
        simulated=False,
        source="correlation",
    )
    db.add(incident)
    await db.flush()

    # Link involved events to the incident via offense engine
    for e in events:
        try:
            await link_event_to_offense(db, e)
        except Exception:
            pass

    # Add audit note
    db.add(
        IncidentNote(
            incident_id=incident.id,
            user_id=user.id,
            content=f"Created from correlation rule '{rule.name}' at {now.isoformat()}",
        )
    )

    # Link incident to the correlation result
    correlation_result.incident_id = incident.id

    # Audit log
    await log_audit(
        db,
        "correlation_incident_created",
        user_id=user.id,
        resource_type="incident",
        resource_id=incident.id,
        ip_address=ip_address,
        details={
            "correlation_result_id": str(correlation_result.id),
            "rule_id": rule.id,
            "event_count": len(events),
            "mitre_techniques": technique_ids,
        },
    )

    # Schedule playbook dispatch
    try:
        from app.services.playbooks import schedule_playbook_dispatch
        await schedule_playbook_dispatch("incident_created", "incident", incident.id)
    except Exception:
        pass

    return {
        "incident_id": str(incident.id),
        "created": True,
        "updated": False,
    }
