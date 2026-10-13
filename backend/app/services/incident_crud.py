"""Incident CRUD — list, get, update, and filter incidents with RBAC and audit."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, and_, or_, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.models.incident import Incident, IncidentNote, IncidentAlert
from app.models.alert import Alert
from app.models.event import Event
from app.models.host import Host
from app.models.user import User
from app.services.audit import log_audit


SEVERITIES = {"critical", "high", "medium", "low", "info"}
VALID_STATUSES = {"open", "investigating", "resolved", "false_positive", "closed"}


async def incident_list(
    db: AsyncSession,
    *,
    severity: str | None = None,
    status: str | None = None,
    host_id: UUID | None = None,
    user_id: UUID | None = None,
    mitre_technique: str | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User | None = None,
) -> dict[str, Any]:
    """List incidents with filters. RBAC: regular users see only their assigned incidents."""
    q = select(Incident)

    # Apply filters
    if severity and severity not in SEVERITIES:
        raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")
    if status and status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    if severity:
        q = q.where(Incident.severity == severity)
    if status:
        q = q.where(Incident.status == status)
    if host_id:
        q = q.where(Incident.host_id == host_id)
    if mitre_technique:
        q = q.where(Incident.mitre_technique_ids.contains([mitre_technique]))

    # Search on title/description
    if search:
        q = q.where(
            or_(
                Incident.title.ilike(f"%{search}%"),
                Incident.description.ilike(f"%{search}%"),
            )
        )

    # RBAC: regular users only see their own assigned incidents
    if current_user and not getattr(current_user, "is_admin", False):
        q = q.where(Incident.created_by == current_user.id)

    # Eager-load relationships for efficient counting/rendering
    q = q.options(
        selectinload(Incident.notes),
        selectinload(Incident.alert_links),
        selectinload(Incident.host),
    )

    # Count total for pagination
    count_q = q.with_only_columns(func.count())
    total = (await db.execute(count_q)).scalar_one()

    # Apply pagination and ordering
    q = q.order_by(Incident.created_at.desc()).offset(skip).limit(limit)
    incidents = (await db.execute(q)).scalars().all()

    return {
        "items": incidents,
        "total": total,
        "skip": skip,
        "limit": limit,
        "pages": (total + limit - 1) // max(limit, 1),
    }


async def incident_get(db: AsyncSession, incident_id: UUID, current_user: User | None = None) -> Incident | None:
    """Get a single incident by ID, with RBAC check."""
    q = (
        select(Incident)
        .options(
            selectinload(Incident.notes),
            selectinload(Incident.alert_links),
            selectinload(Incident.host),
            selectinload(Incident.creator),
        )
        .where(Incident.id == incident_id)
    )
    if current_user and not getattr(current_user, "is_admin", False):
        q = q.where(Incident.created_by == current_user.id)
    incident = (await db.execute(q)).scalar_one_or_none()
    if not incident:
        return None
    # Non-admin users can only access their own incidents
    if current_user and incident.created_by != current_user.id and not getattr(current_user, "is_admin", False):
        return None
    return incident


async def incident_update(
    db: AsyncSession,
    incident_id: UUID,
    *,
    severity: str | None = None,
    status: str | None = None,
    title: str | None = None,
    description: str | None = None,
    current_user: User | None = None,
) -> Incident | None:
    """Update an incident's fields. RBAC: creator or admin only."""
    incident = await incident_get(db, incident_id, current_user=current_user)
    if not incident:
        return None

    # RBAC check: only creator or admin may update
    if (
        current_user
        and incident.created_by != current_user.id
        and not getattr(current_user, "is_admin", False)
    ):
        return None

    now = datetime.now(timezone.utc)
    incident.updated_at = now

    if title is not None:
        incident.title = title
    if description is not None:
        incident.description = description
    if severity is not None:
        if severity not in SEVERITIES:
            raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")
        incident.severity = severity
    if status is not None:
        if status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        incident.status = status
        # If transitioning to resolved/closed, set resolved_at
        if status in ("resolved", "false_positive", "closed"):
            incident.resolved_at = now
        elif status == "open":
            incident.resolved_at = None

    # Audit log
    await log_audit(
        db,
        "incident_updated",
        user_id=current_user.id if current_user else None,
        resource_type="incident",
        resource_id=incident.id,
        details={
            "changed_fields": {k: v for k, v in {
                "severity": severity,
                "status": status,
                "title": title,
                "description": description,
            }.items() if v is not None},
        },
    )

    await db.flush()
    return incident


async def incident_add_note(
    db: AsyncSession,
    incident_id: UUID,
    user: User,
    content: str,
    ip_address: str | None = None,
) -> IncidentNote:
    """Add a note to an incident."""
    note = IncidentNote(
        incident_id=incident_id,
        user_id=user.id,
        content=content,
    )
    db.add(note)
    await db.flush()

    await log_audit(
        db,
        "incident_note_added",
        user_id=user.id,
        resource_type="incident",
        resource_id=incident_id,
        ip_address=ip_address,
        details={"note_content_length": len(content)},
    )
    return note


async def incident_add_alert(
    db: AsyncSession,
    incident_id: UUID,
    alert_id: UUID,
) -> IncidentAlert | None:
    """Link an existing alert to an incident (deduplication included)."""
    # Check for duplicate
    stmt = select(IncidentAlert).where(
        IncidentAlert.incident_id == incident_id, IncidentAlert.alert_id == alert_id
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        return existing

    link = IncidentAlert(incident_id=incident_id, alert_id=alert_id)
    db.add(link)
    await db.flush()
    return link