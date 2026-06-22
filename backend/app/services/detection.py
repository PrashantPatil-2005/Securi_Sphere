import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.alert import Alert
from app.models.alert_rule import AlertRule
from app.models.event import Event
from app.models.host import Host
from app.models.metric import Metric
from app.services.maintenance import is_host_in_maintenance
from app.services.notifications import notify_alert
from app.websocket.manager import ws_manager

logger = logging.getLogger(__name__)

SUPPORTED_RULE_TYPES = frozenset({
    "failed_logins",
    "brute_force",
    "high_cpu",
    "high_memory",
    "high_disk",
    "service_failure",
    "agent_offline",
})

DEFAULT_RULES = [
    {"name": "Failed Logins", "rule_type": "failed_logins", "threshold": 5, "window_minutes": 5, "severity": "high"},
    {"name": "Brute Force", "rule_type": "brute_force", "threshold": 10, "window_minutes": 5, "severity": "critical"},
    {"name": "High CPU", "rule_type": "high_cpu", "threshold": 90, "window_minutes": 2, "severity": "medium"},
    {"name": "High Memory", "rule_type": "high_memory", "threshold": 90, "window_minutes": 1, "severity": "medium"},
    {"name": "High Disk", "rule_type": "high_disk", "threshold": 85, "window_minutes": 1, "severity": "high"},
    {"name": "Service Failure", "rule_type": "service_failure", "threshold": 1, "window_minutes": 1, "severity": "high"},
    {"name": "Agent Offline", "rule_type": "agent_offline", "threshold": 90, "window_minutes": 1, "severity": "critical"},
]


async def seed_alert_rules(db: AsyncSession) -> None:
    result = await db.execute(select(func.count()).select_from(AlertRule))
    if result.scalar_one() > 0:
        return
    for rule in DEFAULT_RULES:
        db.add(AlertRule(**rule))


async def create_alert(
    db: AsyncSession,
    host_id,
    title: str,
    description: str,
    severity: str,
    rule_id=None,
    confidence: float | None = None,
    mitre_technique_id: str | None = None,
    mitre_tactic: str | None = None,
) -> Alert | None:
    dedup_filters = [
        Alert.host_id == host_id,
        Alert.status == "open",
    ]
    if rule_id is not None:
        dedup_filters.append(Alert.rule_id == rule_id)
    else:
        dedup_filters.append(Alert.title == title)
    existing = await db.execute(select(Alert).where(*dedup_filters))
    if existing.scalar_one_or_none():
        return None

    alert = Alert(
        host_id=host_id,
        rule_id=rule_id,
        severity=severity,
        title=title,
        description=description,
        status="open",
        confidence=confidence,
        mitre_technique_id=mitre_technique_id,
        mitre_tactic=mitre_tactic,
    )
    db.add(alert)
    await db.flush()
    from app.services.offense_engine import process_new_alert
    await process_new_alert(db, alert)
    from app.jobs.queue import job_queue
    await job_queue.enqueue("notify_alert", {"alert_id": str(alert.id)})
    await ws_manager.broadcast({
        "type": "new_alert",
        "data": {
            "id": str(alert.id),
            "title": title,
            "severity": severity,
            "confidence": confidence,
            "host_id": str(host_id),
            "timestamp": alert.created_at.isoformat(),
        },
    })
    return alert


async def run_detection_for_host(db: AsyncSession, host: Host) -> None:
    in_maint = await is_host_in_maintenance(db, host.id)
    rules_result = await db.execute(select(AlertRule).where(AlertRule.enabled.is_(True)))
    rules = {r.rule_type: r for r in rules_result.scalars().all()}
    now = datetime.now(timezone.utc)

    bf_rule = rules.get("brute_force")
    fl_rule = rules.get("failed_logins")
    if bf_rule or fl_rule:
        window = max(
            (bf_rule.window_minutes if bf_rule else 0) or 5,
            (fl_rule.window_minutes if fl_rule else 0) or 5,
        )
        since = now - timedelta(minutes=window)
        fail_count = (
            await db.execute(
                select(func.count()).select_from(Event).where(
                    Event.host_id == host.id,
                    Event.event_type == "ssh_login_failure",
                    Event.timestamp >= since,
                )
            )
        ).scalar_one()
        if bf_rule and fail_count >= (bf_rule.threshold or 10):
            await create_alert(
                db, host.id, "Brute Force Attempt",
                f"{fail_count} failed SSH logins detected",
                bf_rule.severity, bf_rule.id,
            )
        elif fl_rule and fail_count >= (fl_rule.threshold or 5):
            await create_alert(
                db, host.id, "Multiple Failed Logins",
                f"{fail_count} failed SSH logins in {fl_rule.window_minutes} minutes",
                fl_rule.severity, fl_rule.id,
            )

    metrics_result = await db.execute(
        select(Metric).where(Metric.host_id == host.id).order_by(Metric.recorded_at.desc()).limit(3)
    )
    recent_metrics = list(metrics_result.scalars().all())

    if recent_metrics and "high_cpu" in rules and not in_maint:
        rule = rules["high_cpu"]
        if len(recent_metrics) >= 3 and all(m.cpu_percent and m.cpu_percent > (rule.threshold or 90) for m in recent_metrics[:3]):
            await create_alert(db, host.id, "High CPU Usage", f"CPU above {rule.threshold}%", rule.severity, rule.id)

    if recent_metrics and "high_memory" in rules and not in_maint:
        rule = rules["high_memory"]
        latest = recent_metrics[0]
        if latest.memory_percent and latest.memory_percent > (rule.threshold or 90):
            await create_alert(db, host.id, "High Memory Usage", f"Memory at {latest.memory_percent:.1f}%", rule.severity, rule.id)

    if recent_metrics and "high_disk" in rules and not in_maint:
        rule = rules["high_disk"]
        latest = recent_metrics[0]
        if latest.disk_percent and latest.disk_percent > (rule.threshold or 85):
            await create_alert(db, host.id, "High Disk Usage", f"Disk at {latest.disk_percent:.1f}%", rule.severity, rule.id)


async def check_service_failure_event(db: AsyncSession, host: Host, event_type: str) -> None:
    if event_type != "service_failure":
        return
    rules_result = await db.execute(select(AlertRule).where(AlertRule.rule_type == "service_failure"))
    rule = rules_result.scalar_one_or_none()
    if rule:
        await create_alert(db, host.id, "Service Failure", "A service failure was detected", rule.severity, rule.id)


async def update_host_statuses(db: AsyncSession) -> None:
    now = datetime.now(timezone.utc)
    hosts_result = await db.execute(select(Host))
    hosts = hosts_result.scalars().all()

    for host in hosts:
        old_status = host.status

        # Hosts awaiting agent install stay offline — no false critical/offline alerts.
        if not host.api_key_hash:
            if host.status != "offline":
                host.status = "offline"
                await ws_manager.broadcast({
                    "type": "host_status",
                    "data": {"id": str(host.id), "status": host.status, "name": host.name},
                })
            continue

        open_alerts = await db.execute(
            select(Alert).where(Alert.host_id == host.id, Alert.status == "open")
        )
        alerts = list(open_alerts.scalars().all())
        critical_alerts = [a for a in alerts if a.severity == "critical"]
        high_alerts = [a for a in alerts if a.severity in ("high", "medium")]

        stale = not host.last_seen or (now - host.last_seen).total_seconds() > 90
        offline = stale

        if offline or critical_alerts:
            host.status = "critical" if critical_alerts or offline else "offline"
            rules_result = await db.execute(select(AlertRule).where(AlertRule.rule_type == "agent_offline"))
            offline_rule = rules_result.scalar_one_or_none()
            open_rule_ids = {a.rule_id for a in alerts if a.rule_id}
            if offline and offline_rule and offline_rule.id not in open_rule_ids:
                if not await is_host_in_maintenance(db, host.id):
                    await create_alert(
                        db, host.id, "Agent Offline",
                        f"Host {host.name} has not sent a heartbeat",
                        offline_rule.severity, offline_rule.id,
                    )
        elif high_alerts:
            host.status = "warning"
        else:
            host.status = "online"

        if old_status != host.status:
            await ws_manager.broadcast({
                "type": "host_status",
                "data": {"id": str(host.id), "status": host.status, "name": host.name},
            })
