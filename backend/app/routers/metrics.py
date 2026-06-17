from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.metric import Metric
from app.models.user import User
from app.schemas.metric import MetricResponse

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("", response_model=list[MetricResponse])
async def list_metrics(
    host_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    from_time: datetime | None = Query(None, alias="from"),
    to_time: datetime | None = Query(None, alias="to"),
    limit: int = Query(500, ge=1, le=2000),
):
    query = select(Metric).where(Metric.host_id == host_id)
    if from_time:
        query = query.where(Metric.recorded_at >= from_time)
    if to_time:
        query = query.where(Metric.recorded_at <= to_time)
    result = await db.execute(query.order_by(Metric.recorded_at.asc()).limit(limit))
    return list(result.scalars().all())
