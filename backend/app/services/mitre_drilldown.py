from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.event import Event
from app.models.host import Host
from app.models.mitre import MitreTechnique
from app.schemas.mitre import (
    MitreDrilldownAlert,
    MitreDrilldownEvent,
    MitreDrilldownHost,
    MitreDrilldownResponse,
)
from app.services.mitre import EVENT_MITRE_MAP, event_technique_clause
from app.utils.query import TimeRange, apply_time_range


async def get_technique_drilldown(
    db: AsyncSession,
    tr: TimeRange,
    technique_id: str,
) -> MitreDrilldownResponse:
    tech = (
        await db.execute(select(MitreTechnique).where(MitreTechnique.technique_id == technique_id))
    ).scalar_one_or_none()

    if not tech:
        mapping = next(
            (m for m in EVENT_MITRE_MAP.values() if m["technique_id"] == technique_id),
            None,
        )
        if not mapping:
            raise HTTPException(status_code=404, detail="MITRE technique not found")
        name = mapping["name"]
        tactic = mapping["tactic"]
        description = None
    else:
        name = tech.name
        tactic = tech.tactic
        description = tech.description

    event_clauses = list(apply_time_range(Event.timestamp, tr))
    event_clauses.append(event_technique_clause(technique_id))

    event_count = (
        await db.execute(select(func.count()).select_from(Event).where(*event_clauses))
    ).scalar_one()

    alert_clauses = list(apply_time_range(Alert.created_at, tr))
    alert_clauses.append(Alert.mitre_technique_id == technique_id)
    alert_count = (
        await db.execute(select(func.count()).select_from(Alert).where(*alert_clauses))
    ).scalar_one()

    top_hosts_rows = (
        await db.execute(
            select(Event.host_id, Host.name, func.count())
            .join(Host, Event.host_id == Host.id)
            .where(*event_clauses)
            .group_by(Event.host_id, Host.name)
            .order_by(func.count().desc())
            .limit(8)
        )
    ).all()
    top_hosts = [
        MitreDrilldownHost(host_id=str(row[0]), host_name=row[1], event_count=row[2])
        for row in top_hosts_rows
    ]

    recent_event_rows = (
        await db.execute(
            select(Event)
            .where(*event_clauses)
            .order_by(Event.timestamp.desc())
            .limit(10)
        )
    ).scalars().all()
    recent_events = [
        MitreDrilldownEvent(
            id=str(e.id),
            host_id=str(e.host_id),
            event_type=e.event_type,
            severity=e.severity,
            description=e.description,
            timestamp=e.timestamp,
        )
        for e in recent_event_rows
    ]

    recent_alert_rows = (
        await db.execute(
            select(Alert)
            .where(*alert_clauses)
            .order_by(Alert.created_at.desc())
            .limit(10)
        )
    ).scalars().all()
    recent_alerts = [
        MitreDrilldownAlert(
            id=str(a.id),
            host_id=str(a.host_id),
            title=a.title,
            severity=a.severity,
            status=a.status,
            created_at=a.created_at,
        )
        for a in recent_alert_rows
    ]

    return MitreDrilldownResponse(
        technique_id=technique_id,
        tactic=tactic,
        name=name,
        description=description,
        event_count=event_count,
        alert_count=alert_count,
        top_hosts=top_hosts,
        recent_events=recent_events,
        recent_alerts=recent_alerts,
    )
