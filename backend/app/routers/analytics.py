import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.database import get_db, get_db_read
from app.dependencies import get_current_user
from app.models.alert import Alert
from app.models.event import Event
from app.models.user import User

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _start_of_day(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def _start_of_week(dt: datetime) -> datetime:
    return _start_of_day(dt - timedelta(days=dt.weekday()))


def _start_of_month(dt: datetime) -> datetime:
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


@router.get("/summary")
async def analytics_summary(db: AsyncSession = Depends(get_db_read), user: User = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    day = _start_of_day(now)
    week = _start_of_week(now)
    month = _start_of_month(now)

    async def count_events(since: datetime):
        return (await db.execute(select(func.count()).select_from(Event).where(Event.timestamp >= since))).scalar_one()

    async def count_alerts(since: datetime):
        return (await db.execute(select(func.count()).select_from(Alert).where(Alert.created_at >= since))).scalar_one()

    return {
        "events_today": await count_events(day),
        "events_this_week": await count_events(week),
        "events_this_month": await count_events(month),
        "alerts_today": await count_alerts(day),
        "alerts_this_week": await count_alerts(week),
        "alerts_this_month": await count_alerts(month),
    }


@router.get("/retention")
async def retention_view(
    view: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    db: AsyncSession = Depends(get_db_read),
    user: User = Depends(get_current_user),
):
    """Bucket counts for the last 90 days (daily/weekly/monthly)."""
    from app.services.analytics.materialized_views import (
        materialized_views_enabled,
        query_retention_from_materialized_views,
    )

    now = datetime.now(timezone.utc)
    since = now.date() - timedelta(days=90)

    if materialized_views_enabled():
        try:
            return await query_retention_from_materialized_views(db, view, since=since)
        except Exception:
            logger.debug("Materialized view query failed, falling back to raw query", exc_info=True)

    since_dt = now - timedelta(days=90)

    if view == "daily":
        event_bucket = func.date_trunc("day", Event.timestamp)
        alert_bucket = func.date_trunc("day", Alert.created_at)
    elif view == "weekly":
        event_bucket = func.date_trunc("week", Event.timestamp)
        alert_bucket = func.date_trunc("week", Alert.created_at)
    else:
        event_bucket = func.date_trunc("month", Event.timestamp)
        alert_bucket = func.date_trunc("month", Alert.created_at)

    events = await db.execute(
        select(event_bucket.label("period"), func.count())
        .where(Event.timestamp >= since_dt)
        .group_by(event_bucket)
        .order_by(event_bucket)
    )
    alerts = await db.execute(
        select(alert_bucket.label("period"), func.count())
        .where(Alert.created_at >= since_dt)
        .group_by(alert_bucket)
        .order_by(alert_bucket)
    )
    return {
        "view": view,
        "since": since_dt.isoformat(),
        "events": [{"period": str(r[0]), "count": r[1]} for r in events.all()],
        "alerts": [{"period": str(r[0]), "count": r[1]} for r in alerts.all()],
    }
