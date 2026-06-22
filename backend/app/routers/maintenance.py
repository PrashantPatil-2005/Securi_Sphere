"""Maintenance windows — suppress routine alerts during planned downtime."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.host import Host
from app.models.maintenance import MaintenanceWindow
from app.models.user import User

router = APIRouter(prefix="/maintenance-windows", tags=["maintenance"])


class MaintenanceCreate(BaseModel):
    host_id: UUID
    reason: str | None = None
    ends_at: datetime


class MaintenanceResponse(BaseModel):
    id: str
    host_id: str
    host_name: str
    reason: str | None
    starts_at: datetime
    ends_at: datetime
    active: bool


@router.get("", response_model=list[MaintenanceResponse])
async def list_windows(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    rows = (
        await db.execute(
            select(MaintenanceWindow, Host.name)
            .join(Host, Host.id == MaintenanceWindow.host_id)
            .where(MaintenanceWindow.ends_at >= now)
            .order_by(MaintenanceWindow.ends_at)
        )
    ).all()
    return [
        MaintenanceResponse(
            id=str(w.id),
            host_id=str(w.host_id),
            host_name=name,
            reason=w.reason,
            starts_at=w.starts_at,
            ends_at=w.ends_at,
            active=w.starts_at <= now <= w.ends_at,
        )
        for w, name in rows
    ]


@router.post("", response_model=MaintenanceResponse)
async def create_window(
    body: MaintenanceCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst")),
):
    host = (await db.execute(select(Host).where(Host.id == body.host_id))).scalar_one_or_none()
    if not host:
        raise HTTPException(404, "Host not found")
    if body.ends_at <= datetime.now(timezone.utc):
        raise HTTPException(400, "ends_at must be in the future")
    row = MaintenanceWindow(
        host_id=body.host_id,
        reason=body.reason,
        created_by=user.id,
        ends_at=body.ends_at,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return MaintenanceResponse(
        id=str(row.id),
        host_id=str(row.host_id),
        host_name=host.name,
        reason=row.reason,
        starts_at=row.starts_at,
        ends_at=row.ends_at,
        active=True,
    )


@router.delete("/{window_id}")
async def delete_window(
    window_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst")),
):
    row = await db.get(MaintenanceWindow, window_id)
    if not row:
        raise HTTPException(404, "Window not found")
    await db.delete(row)
    await db.commit()
    return {"ok": True}
