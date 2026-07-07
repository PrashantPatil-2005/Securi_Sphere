from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.host import Host
from app.models.siem import HostRiskHistory
from app.utils.query import TimeRange, apply_time_range


def choose_risk_bucket(tr: TimeRange) -> str:
    now = datetime.now(timezone.utc)
    start = tr.from_time or now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = tr.to_time or now
    hours = max((end - start).total_seconds() / 3600, 1)
    return "hour" if hours <= 72 else "day"


async def risk_score_trends(
    db: AsyncSession,
    tr: TimeRange,
    host_id: UUID | None = None,
    limit: int = 8,
) -> dict:
    from app.services.siem_analytics import top_risky_hosts

    clauses = list(apply_time_range(HostRiskHistory.recorded_at, tr))
    bucket = choose_risk_bucket(tr)
    bucket_expr = func.date_trunc(bucket, HostRiskHistory.recorded_at)

    fleet_rows = (
        await db.execute(
            select(
                bucket_expr.label("period"),
                func.avg(HostRiskHistory.risk_score),
                func.avg(HostRiskHistory.health_score),
            )
            .where(*clauses)
            .group_by(bucket_expr)
            .order_by(bucket_expr)
        )
    ).all()

    if host_id:
        host_ids = [host_id]
    else:
        top = await top_risky_hosts(db, min(limit, 20))
        host_ids = [UUID(h["host_id"]) for h in top[:limit]]

    hosts_map = {h.id: h.name for h in (await db.execute(select(Host))).scalars().all()}
    series: list[dict] = []

    for hid in host_ids:
        host_clauses = clauses + [HostRiskHistory.host_id == hid]
        points_rows = (
            await db.execute(
                select(HostRiskHistory.risk_score, HostRiskHistory.health_score, HostRiskHistory.recorded_at)
                .where(*host_clauses)
                .order_by(HostRiskHistory.recorded_at)
                .limit(500)
            )
        ).all()
        if not points_rows:
            continue
        points = [
            {
                "recorded_at": ts.isoformat(),
                "risk_score": risk,
                "health_score": health,
            }
            for risk, health, ts in points_rows
        ]
        delta = points[-1]["risk_score"] - points[0]["risk_score"]
        series.append(
            {
                "host_id": str(hid),
                "host_name": hosts_map.get(hid, "?"),
                "current_score": points[-1]["risk_score"],
                "delta": delta,
                "points": points,
            }
        )

    series.sort(key=lambda s: s["current_score"], reverse=True)
    movers = sorted(series, key=lambda s: s["delta"], reverse=True)[:5]

    return {
        "bucket": bucket,
        "fleet_average": [
            {
                "period": row[0].isoformat() if row[0] else "",
                "avg_risk": round(float(row[1] or 0), 1),
                "avg_health": round(float(row[2] or 0), 1),
            }
            for row in fleet_rows
        ],
        "series": series,
        "top_movers": movers,
    }
