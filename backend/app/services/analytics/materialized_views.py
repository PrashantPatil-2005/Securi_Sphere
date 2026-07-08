"""Refresh and query analytics materialized views."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

MV_NAMES = ("mv_events_daily", "mv_alerts_daily", "mv_failed_logins_daily")


def materialized_views_enabled() -> bool:
    return settings.analytics_materialized_views_enabled


def _bucket_sql(view: str, column: str = "bucket_day") -> str:
    if view == "weekly":
        return f"date_trunc('week', {column})::date"
    if view == "monthly":
        return f"date_trunc('month', {column})::date"
    return column


async def refresh_analytics_materialized_views(
    db: AsyncSession,
    *,
    concurrent: bool = True,
) -> dict[str, str]:
    results: dict[str, str] = {}
    for name in MV_NAMES:
        mode = "CONCURRENTLY" if concurrent else ""
        await db.execute(text(f"REFRESH MATERIALIZED VIEW {mode} {name}".strip()))
        results[name] = "refreshed"
    return results


async def materialized_view_status(db: AsyncSession) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            text(
                """
                SELECT matviewname, ispopulated
                FROM pg_matviews
                WHERE schemaname = 'public'
                  AND matviewname = ANY(:names)
                ORDER BY matviewname
                """
            ),
            {"names": list(MV_NAMES)},
        )
    ).all()
    return [{"name": row[0], "populated": row[1]} for row in rows]


async def query_historical_from_materialized_views(
    db: AsyncSession,
    view: str = "daily",
    *,
    since_days: int = 90,
) -> dict[str, Any]:
    since = datetime.now(timezone.utc).date() - timedelta(days=since_days)
    event_bucket = _bucket_sql(view)
    alert_bucket = _bucket_sql(view)

    events = (
        await db.execute(
            text(
                f"""
                SELECT {event_bucket} AS period, SUM(event_count)::bigint AS count
                FROM mv_events_daily
                WHERE bucket_day >= :since
                GROUP BY 1
                ORDER BY 1
                """
            ),
            {"since": since},
        )
    ).all()

    alerts = (
        await db.execute(
            text(
                f"""
                SELECT {alert_bucket} AS period, SUM(alert_count)::bigint AS count
                FROM mv_alerts_daily
                WHERE bucket_day >= :since
                GROUP BY 1
                ORDER BY 1
                """
            ),
            {"since": since},
        )
    ).all()

    hosts = (
        await db.execute(
            text(
                f"""
                SELECT {event_bucket} AS period, COUNT(DISTINCT host_id)::bigint AS active_hosts
                FROM mv_events_daily
                WHERE bucket_day >= :since
                GROUP BY 1
                ORDER BY 1
                """
            ),
            {"since": since},
        )
    ).all()

    from app.models.siem import HostRiskHistory

    risk_trend = await db.execute(
        select(
            func.date_trunc("day", HostRiskHistory.recorded_at).label("period"),
            func.avg(HostRiskHistory.risk_score),
        )
        .where(HostRiskHistory.recorded_at >= datetime.combine(since, datetime.min.time(), tzinfo=timezone.utc))
        .group_by(func.date_trunc("day", HostRiskHistory.recorded_at))
        .order_by(func.date_trunc("day", HostRiskHistory.recorded_at))
    )

    return {
        "view": view,
        "since": datetime.combine(since, datetime.min.time(), tzinfo=timezone.utc).isoformat(),
        "source": "materialized_views",
        "events": [{"period": str(r[0]), "count": int(r[1])} for r in events],
        "alerts": [{"period": str(r[0]), "count": int(r[1])} for r in alerts],
        "hosts": [{"period": str(r[0]), "active_hosts": int(r[1])} for r in hosts],
        "risk_scores": [
            {"period": str(r[0]), "avg_risk": round(float(r[1] or 0), 1)} for r in risk_trend.all()
        ],
    }


async def query_retention_from_materialized_views(
    db: AsyncSession,
    view: str,
    *,
    since: date,
) -> dict[str, Any]:
    event_bucket = _bucket_sql(view)
    alert_bucket = _bucket_sql(view)

    events = (
        await db.execute(
            text(
                f"""
                SELECT {event_bucket} AS period, SUM(event_count)::bigint AS count
                FROM mv_events_daily
                WHERE bucket_day >= :since
                GROUP BY 1
                ORDER BY 1
                """
            ),
            {"since": since},
        )
    ).all()

    alerts = (
        await db.execute(
            text(
                f"""
                SELECT {alert_bucket} AS period, SUM(alert_count)::bigint AS count
                FROM mv_alerts_daily
                WHERE bucket_day >= :since
                GROUP BY 1
                ORDER BY 1
                """
            ),
            {"since": since},
        )
    ).all()

    return {
        "view": view,
        "since": since.isoformat(),
        "source": "materialized_views",
        "events": [{"period": str(r[0]), "count": int(r[1])} for r in events],
        "alerts": [{"period": str(r[0]), "count": int(r[1])} for r in alerts],
    }
