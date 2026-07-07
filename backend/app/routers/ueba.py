"""UEBA baseline anomaly API."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.ueba import UEBA_STATUSES, UebaAnomaly
from app.models.user import User
from app.schemas.ueba import UebaAnomalyResponse, UebaAnomalyUpdate, UebaScanResponse, UebaSummaryResponse
from app.services.audit import log_audit
from app.services.ueba import scan_ueba_anomalies

router = APIRouter(prefix="/ueba", tags=["ueba"])


@router.get("/summary", response_model=UebaSummaryResponse)
async def ueba_summary(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        await db.execute(
            select(UebaAnomaly.severity, func.count())
            .where(UebaAnomaly.status == "open")
            .group_by(UebaAnomaly.severity)
        )
    ).all()
    by_severity = {sev: 0 for sev in ("critical", "high", "medium", "low")}
    total = 0
    for sev, count in rows:
        by_severity[sev] = count
        total += count
    return UebaSummaryResponse(
        open_count=total,
        by_severity=by_severity,
        enabled=settings.ueba_enabled,
        z_threshold=settings.ueba_z_threshold,
        baseline_days=settings.ueba_baseline_days,
    )


@router.get("/anomalies", response_model=list[UebaAnomalyResponse])
async def list_anomalies(
    status: str | None = Query(None),
    severity: str | None = Query(None),
    entity_type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(UebaAnomaly).order_by(UebaAnomaly.detected_at.desc()).limit(limit)
    if status:
        q = q.where(UebaAnomaly.status == status)
    if severity:
        q = q.where(UebaAnomaly.severity == severity)
    if entity_type:
        q = q.where(UebaAnomaly.entity_type == entity_type)
    return list((await db.execute(q)).scalars().all())


@router.patch("/anomalies/{anomaly_id}", response_model=UebaAnomalyResponse)
async def update_anomaly(
    anomaly_id: UUID,
    body: UebaAnomalyUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst")),
):
    if body.status not in ("dismissed", "resolved"):
        raise HTTPException(status_code=400, detail="status must be dismissed or resolved")
    anomaly = (await db.execute(select(UebaAnomaly).where(UebaAnomaly.id == anomaly_id))).scalar_one_or_none()
    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")
    anomaly.status = body.status
    if body.status in UEBA_STATUSES - {"open"}:
        anomaly.resolved_at = datetime.now(timezone.utc)
    await log_audit(db, "ueba_anomaly_updated", user_id=user.id, resource_type="ueba_anomaly", resource_id=anomaly_id, details={"status": body.status})
    return anomaly


@router.post("/scan", response_model=UebaScanResponse)
async def trigger_scan(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst")),
):
    result = await scan_ueba_anomalies(db)
    await log_audit(db, "ueba_scan", user_id=user.id, details=result)
    return UebaScanResponse(**result)
