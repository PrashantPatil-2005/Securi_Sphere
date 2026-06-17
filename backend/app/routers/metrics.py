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
from app.utils.query import ListParams, apply_time_range, resolve_time_range

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("", response_model=list[MetricResponse])
async def list_metrics(
    host_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    preset: str | None = ListParams.preset(),
    from_time: datetime | None = ListParams.from_time(),
    to_time: datetime | None = ListParams.to_time(),
    limit: int = Query(500, ge=1, le=2000),
):
    tr = resolve_time_range(preset, from_time, to_time)
    query = select(Metric).where(Metric.host_id == host_id)
    for clause in apply_time_range(Metric.recorded_at, tr):
        query = query.where(clause)
    result = await db.execute(query.order_by(Metric.recorded_at.asc()).limit(limit))
    return list(result.scalars().all())
