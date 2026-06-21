"""Promote a correlated offense into a formal investigation incident."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.incident import Incident, IncidentAlert, IncidentNote
from app.models.siem import Offense
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

    return {
        "incident_id": str(incident.id),
        "linked_alert_count": linked,
        "created": True,
    }
