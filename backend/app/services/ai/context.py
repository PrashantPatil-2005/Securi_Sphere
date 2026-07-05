"""Load SIEM context from the database for AI responses."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.alert import Alert
from app.models.event import Event
from app.models.host import Host
from app.models.siem import Offense
from app.models.threat_score import HostThreatScore


async def load_alert_context(db: AsyncSession, alert_id: UUID) -> dict | None:
    result = await db.execute(
        select(Alert).options(selectinload(Alert.host)).where(Alert.id == alert_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        return None

    host = alert.host or await db.get(Host, alert.host_id)
    score_row = (
        await db.execute(select(HostThreatScore).where(HostThreatScore.host_id == alert.host_id))
    ).scalar_one_or_none()

    recent_events = (
        await db.execute(
            select(Event)
            .where(Event.host_id == alert.host_id)
            .order_by(Event.timestamp.desc())
            .limit(5)
        )
    ).scalars().all()

    return {
        "type": "alert",
        "alert": {
            "id": str(alert.id),
            "title": alert.title,
            "description": alert.description,
            "severity": alert.severity,
            "status": alert.status,
            "confidence": alert.confidence,
            "mitre_technique_id": alert.mitre_technique_id,
            "mitre_tactic": alert.mitre_tactic,
            "created_at": alert.created_at.isoformat(),
        },
        "host": {
            "id": str(host.id) if host else None,
            "name": host.name if host else "?",
            "hostname": host.hostname if host else None,
            "status": host.status if host else None,
            "ip_address": str(host.ip_address) if host and host.ip_address else None,
            "risk_score": int(score_row.score) if score_row else None,
        },
        "recent_events": [
            {
                "event_type": e.event_type,
                "severity": e.severity,
                "description": e.description,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in recent_events
        ],
    }


async def load_offense_context(db: AsyncSession, offense_id: UUID) -> dict | None:
    result = await db.execute(
        select(Offense).options(selectinload(Offense.links)).where(Offense.id == offense_id)
    )
    offense = result.scalar_one_or_none()
    if not offense:
        return None

    host = await db.get(Host, offense.host_id)
    alert_titles: list[str] = []
    event_types: list[str] = []

    for link in offense.links[:10]:
        if link.alert_id:
            alert = await db.get(Alert, link.alert_id)
            if alert:
                alert_titles.append(alert.title)
        if link.event_id:
            ev = await db.get(Event, link.event_id)
            if ev:
                event_types.append(ev.event_type)

    return {
        "type": "offense",
        "offense": {
            "id": str(offense.id),
            "offense_number": offense.offense_number,
            "title": offense.title,
            "description": offense.description,
            "risk_level": offense.risk_level,
            "status": offense.status,
            "event_count": offense.event_count,
            "alert_count": offense.alert_count,
            "related_hosts": offense.related_hosts or [],
            "related_users": offense.related_users or [],
            "timeline": offense.timeline or [],
            "created_at": offense.created_at.isoformat(),
        },
        "host": {
            "name": host.name if host else "?",
            "status": host.status if host else None,
        },
        "linked_alert_titles": alert_titles[:5],
        "linked_event_types": list(dict.fromkeys(event_types))[:8],
    }
