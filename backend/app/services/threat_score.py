from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.event import Event
from app.models.host import Host
from app.models.metric import Metric
from app.models.threat_score import HostThreatScore


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

    factors = {
        "failed_logins_1h": min(fail_count * 3, 25),
        "critical_alerts": min(critical_alerts * 15, 30),
        "high_alerts": min(high_alerts * 8, 15),
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
        return existing

    row = HostThreatScore(host_id=host.id, score=threat_score, health_score=health_score, factors=factors)
    db.add(row)
    return row


async def update_all_threat_scores(db: AsyncSession) -> None:
    hosts = (await db.execute(select(Host))).scalars().all()
    for host in hosts:
        score_row = await calculate_host_scores(db, host)
        host.health_status = (
            "critical" if score_row.score >= 70 else "warning" if score_row.score >= 40 else "healthy"
        )
