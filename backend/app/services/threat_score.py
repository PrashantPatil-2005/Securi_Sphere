from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.event import Event
from app.models.host import Host
from app.models.metric import Metric
from app.models.threat_score import HostThreatScore
from app.models.siem import HostRiskHistory


async def calculate_host_scores(db: AsyncSession, host: Host) -> HostThreatScore:
    now = datetime.now(timezone.utc)
    since_1h = now - timedelta(hours=1)

    fail_count = (
        await db.execute(
            select(func.count()).select_from(Event).where(
                Event.host_id == host.id,
                Event.event_type == "ssh_login_failure",
                Event.timestamp >= since_1h,
            )
        )
    ).scalar_one()

    critical_alerts = (
        await db.execute(
            select(func.count()).select_from(Alert).where(
                Alert.host_id == host.id, Alert.status == "open", Alert.severity == "critical"
            )
        )
    ).scalar_one()

    high_alerts = (
        await db.execute(
            select(func.count()).select_from(Alert).where(
                Alert.host_id == host.id, Alert.status == "open", Alert.severity == "high"
            )
        )
    ).scalar_one()

    latest_metric = (
        await db.execute(
            select(Metric).where(Metric.host_id == host.id).order_by(Metric.recorded_at.desc()).limit(1)
        )
    ).scalar_one_or_none()

    correlated = (
        await db.execute(
            select(func.count()).select_from(Event).where(
                Event.host_id == host.id,
                Event.severity.in_(["high", "critical"]),
                Event.timestamp >= since_1h,
            )
        )
    ).scalar_one()

    service_failures = (
        await db.execute(
            select(func.count()).select_from(Event).where(
                Event.host_id == host.id,
                Event.event_type == "service_failure",
                Event.timestamp >= since_1h,
            )
        )
    ).scalar_one()

    from app.models.siem import Offense
    open_offenses = (
        await db.execute(
            select(func.count()).select_from(Offense).where(
                Offense.host_id == host.id,
                Offense.status.in_(["open", "investigating"]),
            )
        )
    ).scalar_one()

    factors = {
        "failed_logins": min(fail_count * 3, 25),
        "service_failures": min(service_failures * 5, 15),
        "critical_alerts": min(critical_alerts * 15, 30),
        "high_alerts": min(high_alerts * 8, 15),
        "correlated_security_events": min(correlated * 4, 15),
        "open_offenses": min(open_offenses * 10, 20),
        "agent_offline": 10 if host.status in ("offline", "critical") and not host.last_seen else 0,
        "high_cpu": 0,
        "high_memory": 0,
        "high_disk": 0,
    }

    if latest_metric:
        if latest_metric.cpu_percent and latest_metric.cpu_percent > 90:
            factors["high_cpu"] = 10
        if latest_metric.memory_percent and latest_metric.memory_percent > 90:
            factors["high_memory"] = 10
        if latest_metric.disk_percent and latest_metric.disk_percent > 85:
            factors["high_disk"] = 10

    threat_score = min(int(sum(factors.values())), 100)
    health_score = max(0, 100 - threat_score)

    existing = (
        await db.execute(select(HostThreatScore).where(HostThreatScore.host_id == host.id))
    ).scalar_one_or_none()

    if existing:
        existing.score = threat_score
        existing.health_score = health_score
        existing.factors = factors
        existing.calculated_at = now
        score_row = existing
    else:
        score_row = HostThreatScore(host_id=host.id, score=threat_score, health_score=health_score, factors=factors)
        db.add(score_row)

    last_hist = (
        await db.execute(
            select(HostRiskHistory)
            .where(HostRiskHistory.host_id == host.id)
            .order_by(HostRiskHistory.recorded_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    should_record = (
        not last_hist
        or (now - last_hist.recorded_at).total_seconds() >= 3600
        or abs(last_hist.risk_score - threat_score) >= 5
    )
    if should_record:
        db.add(
            HostRiskHistory(
                host_id=host.id,
                risk_score=threat_score,
                health_score=health_score,
                factors=factors,
                recorded_at=now,
            )
        )
    return score_row


async def update_all_threat_scores(db: AsyncSession) -> None:
    hosts = (await db.execute(select(Host))).scalars().all()
    for host in hosts:
        score_row = await calculate_host_scores(db, host)
        host.health_status = (
            "critical" if score_row.score >= 70 else "warning" if score_row.score >= 40 else "healthy"
        )
