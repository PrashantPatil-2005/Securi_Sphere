from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.incident import Incident, IncidentAlert, IncidentNote
from app.models.user import User
from app.services.audit import log_audit

router = APIRouter(prefix="/incidents", tags=["incidents"])


class IncidentCreate(BaseModel):
    title: str
    description: str | None = None
    severity: str = "medium"
    host_id: UUID | None = None


class NoteCreate(BaseModel):
    content: str


class IncidentResponse(BaseModel):
    id: UUID
    title: str
    description: str | None
    severity: str
    status: str
    host_id: UUID | None
    assigned_to: UUID | None
    created_at: datetime
    resolved_at: datetime | None
    model_config = {"from_attributes": True}


class IncidentDetailResponse(IncidentResponse):
    notes: list[dict] = []
    alert_ids: list[str] = []


@router.get("/{incident_id}", response_model=IncidentDetailResponse)
async def get_incident(
    incident_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    inc = (
        await db.execute(
            select(Incident)
            .options(selectinload(Incident.notes), selectinload(Incident.alert_links))
            .where(Incident.id == incident_id)
        )
    ).scalar_one_or_none()
    if not inc:
        raise HTTPException(status_code=404, detail="Not found")
    return IncidentDetailResponse(
        id=inc.id,
        title=inc.title,
        description=inc.description,
        severity=inc.severity,
        status=inc.status,
        host_id=inc.host_id,
        assigned_to=inc.assigned_to,
        created_at=inc.created_at,
        resolved_at=inc.resolved_at,
        notes=[{"id": str(n.id), "content": n.content, "user_id": str(n.user_id), "created_at": n.created_at.isoformat()} for n in inc.notes],
        alert_ids=[str(l.alert_id) for l in inc.alert_links],
    )


@router.get("", response_model=list[IncidentResponse])
async def list_incidents(status: str | None = None, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    q = select(Incident).order_by(Incident.created_at.desc())
    if status:
        q = q.where(Incident.status == status)
    return list((await db.execute(q)).scalars().all())


@router.post("", response_model=IncidentResponse)
async def create_incident(body: IncidentCreate, db: AsyncSession = Depends(get_db), user=Depends(require_roles("admin", "analyst"))):
    inc = Incident(title=body.title, description=body.description, severity=body.severity, host_id=body.host_id, created_by=user.id)
    db.add(inc)
    await db.flush()
    await log_audit(db, "incident_create", user_id=user.id, resource_type="incident", resource_id=inc.id)
    from app.services.playbooks import schedule_playbook_dispatch
    await schedule_playbook_dispatch("incident_created", "incident", inc.id)
    return inc


@router.patch("/{incident_id}/status")
async def update_status(incident_id: UUID, status: str, db: AsyncSession = Depends(get_db), user=Depends(require_roles("admin", "analyst"))):
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    inc = result.scalar_one_or_none()
    if not inc:
        raise HTTPException(status_code=404, detail="Not found")
    inc.status = status
    inc.updated_at = datetime.now(timezone.utc)
    if status in ("resolved", "closed"):
        inc.resolved_at = datetime.now(timezone.utc)
    return inc


@router.post("/{incident_id}/notes")
async def add_note(incident_id: UUID, body: NoteCreate, db: AsyncSession = Depends(get_db), user=Depends(require_roles("admin", "analyst"))):
    db.add(IncidentNote(incident_id=incident_id, user_id=user.id, content=body.content))
    return {"message": "note added"}


@router.post("/{incident_id}/alerts/{alert_id}")
async def link_alert(incident_id: UUID, alert_id: UUID, db: AsyncSession = Depends(get_db), user=Depends(require_roles("admin", "analyst"))):
    db.add(IncidentAlert(incident_id=incident_id, alert_id=alert_id))
    return {"message": "linked"}
