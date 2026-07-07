"""Analytics aggregation — pre-compute daily stats from raw tables."""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.analytics import AnalyticsDailyStat
from app.models.event import Event
from app.models.siem import HostRiskHistory, Offense


async def aggregate_daily_stats(db: AsyncSession, stat_date: date | None = None) -> int:
    """Roll up raw events/alerts into analytics_daily_stats. Returns rows upserted."""
    target = stat_date or (datetime.now(timezone.utc).date() - timedelta(days=1))
    day_start = datetime.combine(target, datetime.min.time(), tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)
    upserted = 0

    event_counts = (
        await db.execute(
            select(Event.event_type, func.count())
            .where(Event.timestamp >= day_start, Event.timestamp < day_end)
            .group_by(Event.event_type)
        )
    ).all()
    for event_type, count in event_counts:
        await _upsert_stat(db, target, "events_by_type", event_type, count, {"event_type": event_type})
        upserted += 1

    fail_count = (
        await db.execute(
            select(func.count()).select_from(Event).where(
                Event.timestamp >= day_start,
                Event.timestamp < day_end,
                Event.event_type == "ssh_login_failure",
            )
        )
    ).scalar_one()
    await _upsert_stat(db, target, "failed_logins", "global", fail_count, {})
    upserted += 1

    for severity in ("critical", "high", "medium", "low"):
        count = (
            await db.execute(
                select(func.count()).select_from(Alert).where(
                    Alert.created_at >= day_start,
                    Alert.created_at < day_end,
                    Alert.severity == severity,
                )
            )
        ).scalar_one()
        await _upsert_stat(db, target, "alerts_by_severity", severity, count, {"severity": severity})
        upserted += 1

    offense_count = (
        await db.execute(
            select(func.count()).select_from(Offense).where(
                Offense.created_at >= day_start,
                Offense.created_at < day_end,
            )
        )
    ).scalar_one()
    await _upsert_stat(db, target, "offenses", "global", offense_count, {})
    upserted += 1

    avg_risk = (
        await db.execute(
            select(func.avg(HostRiskHistory.risk_score)).where(
                HostRiskHistory.recorded_at >= day_start,
                HostRiskHistory.recorded_at < day_end,
            )
        )
    ).scalar_one()
    if avg_risk:
        await _upsert_stat(db, target, "avg_risk_score", "global", int(avg_risk), {})
        upserted += 1

    upserted += await _aggregate_ueba_host_stats(db, target, day_start, day_end)
    upserted += await _aggregate_ueba_user_stats(db, target, day_start, day_end)

    return upserted


AUTH_EVENT_TYPES = frozenset({
    "ssh_login_failure",
    "ssh_login_success",
    "sudo_usage",
    "root_login",
})


async def _aggregate_ueba_host_stats(
    db: AsyncSession,
    target,
    day_start: datetime,
    day_end: datetime,
) -> int:
    count = 0
    host_totals = (
        await db.execute(
            select(Event.host_id, func.count())
            .where(Event.timestamp >= day_start, Event.timestamp < day_end)
            .group_by(Event.host_id)
        )
    ).all()
    for host_id, total in host_totals:
        await _upsert_stat(db, target, "ueba_events_total", str(host_id), total, {"host_id": str(host_id)})
        count += 1

    host_fails = (
        await db.execute(
            select(Event.host_id, func.count())
            .where(
                Event.timestamp >= day_start,
                Event.timestamp < day_end,
                Event.event_type == "ssh_login_failure",
            )
            .group_by(Event.host_id)
        )
    ).all()
    for host_id, fails in host_fails:
        await _upsert_stat(db, target, "ueba_failed_logins", str(host_id), fails, {"host_id": str(host_id)})
        count += 1

    host_auth = (
        await db.execute(
            select(Event.host_id, func.count())
            .where(
                Event.timestamp >= day_start,
                Event.timestamp < day_end,
                Event.event_type.in_(AUTH_EVENT_TYPES),
            )
            .group_by(Event.host_id)
        )
    ).all()
    for host_id, auth_count in host_auth:
        await _upsert_stat(db, target, "ueba_auth_events", str(host_id), auth_count, {"host_id": str(host_id)})
        count += 1
    return count


async def _aggregate_ueba_user_stats(
    db: AsyncSession,
    target,
    day_start: datetime,
    day_end: datetime,
) -> int:
    count = 0
    user_fails = (
        await db.execute(
            select(Event.username, func.count())
            .where(
                Event.timestamp >= day_start,
                Event.timestamp < day_end,
                Event.event_type == "ssh_login_failure",
                Event.username.isnot(None),
            )
            .group_by(Event.username)
        )
    ).all()
    for username, fails in user_fails:
        await _upsert_stat(db, target, "ueba_failed_logins", username, fails, {"username": username})
        count += 1

    user_auth = (
        await db.execute(
            select(Event.username, func.count())
            .where(
                Event.timestamp >= day_start,
                Event.timestamp < day_end,
                Event.event_type.in_(AUTH_EVENT_TYPES),
                Event.username.isnot(None),
            )
            .group_by(Event.username)
        )
    ).all()
    for username, auth_count in user_auth:
        await _upsert_stat(db, target, "ueba_auth_events", username, auth_count, {"username": username})
        count += 1
    return count


async def _upsert_stat(
    db: AsyncSession,
    stat_date: date,
    metric_name: str,
    dimension_key: str,
    value: int,
    breakdown: dict,
) -> None:
    stmt = insert(AnalyticsDailyStat).values(
        stat_date=stat_date,
        metric_name=metric_name,
        dimension_key=dimension_key,
        value=value,
        breakdown=breakdown,
        updated_at=datetime.now(timezone.utc),
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_daily_stat",
        set_={"value": value, "breakdown": breakdown, "updated_at": datetime.now(timezone.utc)},
    )
    await db.execute(stmt)


async def query_trend(
    db: AsyncSession,
    metric_name: str,
    days: int = 30,
    dimension_key: str = "global",
) -> list[dict]:
    since = datetime.now(timezone.utc).date() - timedelta(days=days)
    rows = (
        await db.execute(
            select(AnalyticsDailyStat)
            .where(
                AnalyticsDailyStat.metric_name == metric_name,
                AnalyticsDailyStat.dimension_key == dimension_key,
                AnalyticsDailyStat.stat_date >= since,
            )
            .order_by(AnalyticsDailyStat.stat_date)
        )
    ).scalars().all()
    return [{"date": r.stat_date.isoformat(), "value": r.value, "breakdown": r.breakdown} for r in rows]
