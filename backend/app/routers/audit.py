from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.audit import AuditLog
from app.models.user import User

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditResponse(BaseModel):
    id: UUID
    user_id: UUID | None
    action: str
    resource_type: str | None
    resource_id: UUID | None
    ip_address: str | None
    details: dict | None
    timestamp: datetime
    model_config = {"from_attributes": True}


@router.get("", response_model=list[AuditResponse])
async def list_audit_logs(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin")),
    action: str | None = None,
    from_time: datetime | None = Query(None, alias="from"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    q = select(AuditLog).order_by(AuditLog.timestamp.desc())
    if action:
        q = q.where(AuditLog.action == action)
    if from_time:
        q = q.where(AuditLog.timestamp >= from_time)
    q = q.offset((page - 1) * page_size).limit(page_size)
    return list((await db.execute(q)).scalars().all())
