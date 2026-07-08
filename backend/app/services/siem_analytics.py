"""SIEM analytics queries — all respect time range and host filters."""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import case, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import String

from app.models.alert import Alert
from app.models.event import Event
from app.models.host import Host
from app.models.metric import Metric
from app.models.threat_score import HostThreatScore
from app.models.timeline import AttackTimeline
from app.utils.query import TimeRange, apply_time_range
from app.utils.simulation_filter import real_events_only, should_exclude_simulated

AUTH_TYPES = {"ssh_login_failure", "ssh_login_success", "root_login"}
SERVICE_TYPES = {"service_failure", "service_start", "service_stop"}
SSH_TYPES = {"ssh_login_failure", "ssh_login_success", "root_login"}
SUDO_TYPES = {"sudo_usage"}
SECURITY_TYPES = {"ssh_login_failure", "brute_force", "sudo_usage", "root_login"}
SYSTEM_TYPES = {"high_cpu", "high_memory", "high_disk", "agent_offline"}
NETWORK_TYPES: set[str] = set()

EVENT_CATEGORIES = {
    "authentication": AUTH_TYPES,
    "ssh": SSH_TYPES,
    "sudo": SUDO_TYPES,
    "service": SERVICE_TYPES,
    "system": SYSTEM_TYPES,
    "network": NETWORK_TYPES,
    "security": SECURITY_TYPES,
}

SEVERITY_LEVELS = ["critical", "high", "medium", "low", "info"]


def _event_clauses(tr: TimeRange, host_id: UUID | None = None, include_simulated: bool | None = None) -> list:
    clauses = list(apply_time_range(Event.timestamp, tr))
    if host_id:
        clauses.append(Event.host_id == host_id)
    if should_exclude_simulated(include_simulated):
        clauses.append(real_events_only())
    return clauses


def _granularity(tr: TimeRange) -> str:
    span = (tr.to_time or datetime.now(timezone.utc)) - (
        tr.from_time or datetime.now(timezone.utc) - timedelta(days=1)
    )
    return "hour" if span <= timedelta(hours=25) else "day"


def _bucket_column(column, tr: TimeRange):
    if _granularity(tr) == "hour":
        return func.date_trunc("hour", column)
    return func.date_trunc("day", column)


def _risk_color(score: int) -> str:
    if score >= 70:
        return "red"
    if score >= 50:
        return "orange"
    if score >= 30:
        return "yellow"
    return "green"


def _health_status(score: int, host_status: str) -> str:
    if score >= 70 or host_status == "critical":
        return "critical"
    if score >= 40 or host_status in ("offline", "warning"):
        return "warning"
    return "healthy"


async def events_trend(
    db: AsyncSession,
    tr: TimeRange,
    host_id: UUID | None = None,
) -> dict:
    bucket = _bucket_column(Event.timestamp, tr)
    clauses = _event_clauses(tr, host_id)

    async def run(extra_clauses: list):
        q = (
            select(bucket.label("period"), func.count().label("count"))
            .where(*clauses, *extra_clauses)
            .group_by(bucket)
            .order_by(bucket)
        )
        return [{"period": str(r[0]), "count": r[1]} for r in (await db.execute(q)).all()]

    return {
        "granularity": _granularity(tr),
        "total": await run([]),
        "security": await run([or_(Event.event_type.in_(SECURITY_TYPES), Event.severity.in_(["high", "critical"]))]),
        "authentication": await run([Event.event_type.in_(AUTH_TYPES)]),
        "service": await run([Event.event_type.in_(SERVICE_TYPES)]),
    }


async def failed_login_analytics(db: AsyncSession, tr: TimeRange, host_id: UUID | None = None) -> dict:
    clauses = _event_clauses(tr, host_id) + [Event.event_type == "ssh_login_failure"]

    bucket = _bucket_column(Event.timestamp, tr)
    over_time = await db.execute(
        select(bucket.label("period"), func.count())
        .where(*clauses)
        .group_by(bucket)
        .order_by(bucket)
    )

    by_host = await db.execute(
        select(Host.name, func.count())
        .join(Event, Event.host_id == Host.id)
        .where(*clauses)
        .group_by(Host.name)
        .order_by(func.count().desc())
        .limit(20)
    )

    by_user = await db.execute(
        select(Event.username, func.count())
        .where(*clauses, Event.username.isnot(None))
        .group_by(Event.username)
        .order_by(func.count().desc())
        .limit(20)
    )

    by_ip = await db.execute(
        select(cast(Event.source_ip, String).label("source_ip"), func.count())
        .where(*clauses, Event.source_ip.isnot(None))
        .group_by(Event.source_ip)
        .order_by(func.count().desc())
        .limit(20)
    )

    suspicious = []
    for ip, cnt in by_ip.all():
        if cnt >= 5:
            suspicious.append({"source_ip": ip, "failed_attempts": cnt, "severity": "high" if cnt >= 10 else "medium"})

    return {
        "over_time": [{"period": str(r[0]), "count": r[1]} for r in over_time.all()],
        "by_host": [{"host": r[0], "count": r[1]} for r in by_host.all()],
        "by_user": [{"username": r[0] or "unknown", "count": r[1]} for r in by_user.all()],
        "by_source_ip": [{"source_ip": r[0] or "unknown", "count": r[1]} for r in by_ip.all()],
        "top_attacking_ips": [{"source_ip": r[0], "count": r[1]} for r in by_ip.all()[:10]],
        "most_targeted_accounts": [{"username": r[0], "count": r[1]} for r in by_user.all()[:10]],
        "suspicious_alerts": suspicious,
    }


async def severity_distribution(
    db: AsyncSession,
    tr: TimeRange,
    host_id: UUID | None = None,
    status: str | None = None,
) -> dict:
    clauses = apply_time_range(Alert.created_at, tr)
    if host_id:
        clauses.append(Alert.host_id == host_id)
    if status:
        clauses.append(Alert.status == status)

    rows = await db.execute(
        select(Alert.severity, func.count()).where(*clauses).group_by(Alert.severity)
    )
    counts = {r[0]: r[1] for r in rows.all()}
    total = sum(counts.values()) or 1
    distribution = []
    for sev in SEVERITY_LEVELS:
        c = counts.get(sev, 0)
        distribution.append({"severity": sev, "count": c, "percentage": round(c / total * 100, 1)})
    return {"total": sum(counts.values()), "distribution": distribution}


async def event_type_distribution(db: AsyncSession, tr: TimeRange, host_id: UUID | None = None) -> dict:
    clauses = _event_clauses(tr, host_id)

    events = list((await db.execute(select(Event.event_type).where(*clauses))).scalars().all())
    category_counts: dict[str, int] = {k: 0 for k in EVENT_CATEGORIES}
    uncategorized = 0
    for et in events:
        matched = False
        for cat, types in EVENT_CATEGORIES.items():
            if et in types:
                category_counts[cat] += 1
                matched = True
                break
        if not matched:
            uncategorized += 1
    if uncategorized:
        category_counts["other"] = uncategorized

    bucket = _bucket_column(Event.timestamp, tr)
    trend_rows = await db.execute(
        select(bucket.label("period"), Event.event_type, func.count())
        .where(*clauses)
        .group_by(bucket, Event.event_type)
        .order_by(bucket)
    )
    trend: dict[str, dict[str, int]] = {}
    for period, etype, cnt in trend_rows.all():
        key = str(period)
        trend.setdefault(key, {})
        for cat, types in EVENT_CATEGORIES.items():
            if etype in types:
                trend[key][cat] = trend[key].get(cat, 0) + cnt
                break

    return {
        "categories": [{"category": k, "count": v} for k, v in category_counts.items() if v > 0],
        "trend": [{"period": p, **cats} for p, cats in sorted(trend.items())],
    }


async def top_risky_hosts(db: AsyncSession, limit: int = 20) -> list[dict]:
    hosts = {h.id: h for h in (await db.execute(select(Host))).scalars().all()}
    scores = (
        await db.execute(select(HostThreatScore).order_by(HostThreatScore.score.desc()).limit(limit))
    ).scalars().all()

    result = []
    for s in scores:
        host = hosts.get(s.host_id)
        open_alerts = (
            await db.execute(
                select(func.count()).select_from(Alert).where(
                    Alert.host_id == s.host_id, Alert.status.in_(["open", "investigating"])
                )
            )
        ).scalar_one()
        result.append({
            "host_id": str(s.host_id),
            "host_name": host.name if host else "?",
            "risk_score": s.score,
            "health_score": s.health_score,
            "active_alerts": open_alerts,
            "last_seen": host.last_seen.isoformat() if host and host.last_seen else None,
            "color": _risk_color(s.score),
            "factors": s.factors or {},
        })
    return result


async def host_risk_dashboard(db: AsyncSession, tr: TimeRange, host_id: UUID | None = None) -> dict:
    from app.models.siem import HostRiskHistory

    clauses = apply_time_range(HostRiskHistory.recorded_at, tr)
    if host_id:
        clauses.append(HostRiskHistory.host_id == host_id)

    history = await db.execute(
        select(HostRiskHistory.host_id, HostRiskHistory.risk_score, HostRiskHistory.recorded_at)
        .where(*clauses)
        .order_by(HostRiskHistory.recorded_at)
    )

    hosts_map = {h.id: h.name for h in (await db.execute(select(Host))).scalars().all()}
    by_host: dict[str, list] = {}
    for hid, score, ts in history.all():
        key = str(hid)
        by_host.setdefault(key, []).append({"score": score, "recorded_at": ts.isoformat()})

    current = await top_risky_hosts(db, 10)
    return {"current": current, "history": by_host, "host_names": {str(k): v for k, v in hosts_map.items()}}


async def host_health_monitoring(db: AsyncSession) -> dict:
    hosts = list((await db.execute(select(Host))).scalars().all())
    scores = {s.host_id: s for s in (await db.execute(select(HostThreatScore))).scalars().all()}
    from app.models.siem import HostRiskHistory

    result = []
    for host in hosts:
        s = scores.get(host.id)
        risk = s.score if s else 0
        health = s.health_score if s else 100
        status = _health_status(risk, host.status or "online")

        latest_metric = (
            await db.execute(
                select(Metric).where(Metric.host_id == host.id).order_by(Metric.recorded_at.desc()).limit(1)
            )
        ).scalar_one_or_none()

        open_alerts = (
            await db.execute(
                select(func.count()).select_from(Alert).where(
                    Alert.host_id == host.id, Alert.status.in_(["open", "investigating"])
                )
            )
        ).scalar_one()

        hist = (
            await db.execute(
                select(HostRiskHistory.health_score, HostRiskHistory.recorded_at)
                .where(HostRiskHistory.host_id == host.id)
                .order_by(HostRiskHistory.recorded_at.desc())
                .limit(48)
            )
        ).all()

        result.append({
            "host_id": str(host.id),
            "host_name": host.name,
            "health_score": health,
            "health_status": status,
            "agent_status": host.status,
            "active_alerts": open_alerts,
            "cpu_percent": latest_metric.cpu_percent if latest_metric else None,
            "memory_percent": latest_metric.memory_percent if latest_metric else None,
            "disk_percent": latest_metric.disk_percent if latest_metric else None,
            "history": [{"health_score": h[0], "recorded_at": h[1].isoformat()} for h in reversed(hist)],
        })
    return {"hosts": result}


async def executive_summary(db: AsyncSession, tr: TimeRange) -> dict:
    event_clauses = _event_clauses(tr)
    alert_clauses = apply_time_range(Alert.created_at, tr)

    total_hosts = (await db.execute(select(func.count()).select_from(Host))).scalar_one()
    online_hosts = (await db.execute(select(func.count()).select_from(Host).where(Host.status == "online"))).scalar_one()
    active_alerts = (
        await db.execute(select(func.count()).select_from(Alert).where(Alert.status.in_(["open", "investigating"])))
    ).scalar_one()
    critical_alerts = (
        await db.execute(
            select(func.count()).select_from(Alert).where(
                Alert.status.in_(["open", "investigating"]), Alert.severity == "critical"
            )
        )
    ).scalar_one()
    total_events = (await db.execute(select(func.count()).select_from(Event).where(*event_clauses))).scalar_one()
    period_alerts = (await db.execute(select(func.count()).select_from(Alert).where(*alert_clauses))).scalar_one()

    avg_risk = (await db.execute(select(func.avg(HostThreatScore.score)))).scalar_one() or 0

    attacked = await db.execute(
        select(Host.name, func.count().label("cnt"))
        .join(Event, Event.host_id == Host.id)
        .where(*event_clauses, Event.event_type == "ssh_login_failure")
        .group_by(Host.name)
        .order_by(func.count().desc())
        .limit(1)
    )
    top = attacked.first()

    trend = await events_trend(db, tr)
    return {
        "total_hosts": total_hosts,
        "online_hosts": online_hosts,
        "active_alerts": active_alerts,
        "critical_alerts": critical_alerts,
        "total_events": total_events,
        "period_alerts": period_alerts,
        "average_risk_score": round(float(avg_risk), 1),
        "most_attacked_host": top[0] if top else None,
        "most_attacked_count": top[1] if top else 0,
        "security_trend": trend["security"],
    }


async def mitre_stats(db: AsyncSession, tr: TimeRange, host_id: UUID | None = None) -> dict:
    clauses = _event_clauses(tr, host_id)

    rows = await db.execute(
        select(Event.mitre_tactic, Event.mitre_technique_id, func.count())
        .where(*clauses, Event.mitre_tactic.isnot(None))
        .group_by(Event.mitre_tactic, Event.mitre_technique_id)
        .order_by(func.count().desc())
    )

    tactics: dict[str, list] = {}
    techniques = []
    for tactic, tid, cnt in rows.all():
        entry = {"technique_id": tid, "tactic": tactic, "count": cnt}
        techniques.append(entry)
        tactics.setdefault(tactic or "Unknown", []).append(entry)
    return {"tactics": tactics, "techniques": techniques}


async def historical_analytics(db: AsyncSession, view: str = "daily") -> dict:
    from app.services.analytics.materialized_views import (
        materialized_views_enabled,
        query_historical_from_materialized_views,
    )

    if materialized_views_enabled():
        try:
            return await query_historical_from_materialized_views(db, view)
        except Exception:
            pass

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=90)
    if view == "daily":
        eb, ab = func.date_trunc("day", Event.timestamp), func.date_trunc("day", Alert.created_at)
    elif view == "weekly":
        eb, ab = func.date_trunc("week", Event.timestamp), func.date_trunc("week", Alert.created_at)
    else:
        eb, ab = func.date_trunc("month", Event.timestamp), func.date_trunc("month", Alert.created_at)

    hist_event_clauses = [Event.timestamp >= since]
    if should_exclude_simulated():
        hist_event_clauses.append(real_events_only())
    events = await db.execute(
        select(eb.label("period"), func.count()).where(*hist_event_clauses).group_by(eb).order_by(eb)
    )
    alerts = await db.execute(
        select(ab.label("period"), func.count()).where(Alert.created_at >= since).group_by(ab).order_by(ab)
    )

    host_trend = await db.execute(
        select(eb.label("period"), func.count(func.distinct(Event.host_id)))
        .where(*hist_event_clauses)
        .group_by(eb)
        .order_by(eb)
    )

    from app.models.siem import HostRiskHistory
    risk_trend = await db.execute(
        select(func.date_trunc("day", HostRiskHistory.recorded_at).label("period"), func.avg(HostRiskHistory.risk_score))
        .where(HostRiskHistory.recorded_at >= since)
        .group_by(func.date_trunc("day", HostRiskHistory.recorded_at))
        .order_by(func.date_trunc("day", HostRiskHistory.recorded_at))
    )

    return {
        "view": view,
        "since": since.isoformat(),
        "events": [{"period": str(r[0]), "count": r[1]} for r in events.all()],
        "alerts": [{"period": str(r[0]), "count": r[1]} for r in alerts.all()],
        "hosts": [{"period": str(r[0]), "active_hosts": r[1]} for r in host_trend.all()],
        "risk_scores": [{"period": str(r[0]), "avg_risk": round(float(r[1] or 0), 1)} for r in risk_trend.all()],
    }


async def attack_timeline_list(
    db: AsyncSession,
    tr: TimeRange,
    host_id: UUID | None = None,
) -> list[dict]:
    clauses = apply_time_range(AttackTimeline.started_at, tr)
    if host_id:
        clauses.append(AttackTimeline.host_id == host_id)

    timelines = (
        await db.execute(select(AttackTimeline).where(*clauses).order_by(AttackTimeline.started_at.desc()).limit(50))
    ).scalars().all()
    hosts = {h.id: h.name for h in (await db.execute(select(Host))).scalars().all()}

    result = []
    for t in timelines:
        event_details = []
        if t.event_ids:
            from uuid import UUID as PyUUID
            uuids = [PyUUID(eid) for eid in t.event_ids if eid]
            evs = (
                await db.execute(select(Event).where(Event.id.in_(uuids)).order_by(Event.timestamp))
            ).scalars().all()
            event_details = [
                {
                    "event_type": e.event_type,
                    "description": e.description,
                    "timestamp": e.timestamp.isoformat(),
                    "severity": e.severity,
                }
                for e in evs
            ]
        result.append({
            "id": str(t.id),
            "host_id": str(t.host_id),
            "host_name": hosts.get(t.host_id, "?"),
            "title": t.title,
            "started_at": t.started_at.isoformat(),
            "ended_at": t.ended_at.isoformat() if t.ended_at else None,
            "events": event_details,
            "risk_level": t.severity,
        })
    return result
