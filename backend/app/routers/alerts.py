from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.alert import Alert
from app.models.user import User
from app.schemas.alert import AlertListResponse, AlertResponse
from app.services.detection import update_host_statuses
from app.websocket.manager import ws_manager

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    status: str | None = None,
    severity: str | None = None,
    host_id: UUID | None = None,
):
    query = select(Alert)
    count_query = select(func.count()).select_from(Alert)
    if status:
        query = query.where(Alert.status == status)
        count_query = count_query.where(Alert.status == status)
    if severity:
        query = query.where(Alert.severity == severity)
        count_query = count_query.where(Alert.severity == severity)
    if host_id:
        query = query.where(Alert.host_id == host_id)
        count_query = count_query.where(Alert.host_id == host_id)

    total = (await db.execute(count_query)).scalar_one()
    result = await db.execute(query.order_by(Alert.created_at.desc()).limit(200))
    return AlertListResponse(items=list(result.scalars().all()), total=total)


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.patch("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst")),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = "resolved"
    alert.resolved_at = datetime.now(timezone.utc)
    alert.resolved_by = user.id
    await update_host_statuses(db)
    await ws_manager.broadcast({"type": "alert_resolved", "data": {"id": str(alert.id)}})
    return alert
