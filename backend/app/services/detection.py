"""Extensible detection engine — rule registry pattern.

Instead of 7 hardcoded if/else blocks, each rule type is a self-contained
checker class. Adding a new detection rule means writing one class and
registering it — no changes to the engine loop.

This is the actual architecture, not marketing.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.alert import Alert
from app.models.alert_rule import AlertRule
from app.models.event import Event
from app.models.host import Host
from app.models.metric import Metric
from app.services.maintenance import is_host_in_maintenance
from app.websocket.manager import ws_manager

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rule type registry
# ---------------------------------------------------------------------------

class RuleChecker(ABC):
    """Base class for all detection rule checkers.

    Each subclass implements:
    - `check()`: query the DB for conditions, return alert args or None
    - `description`: human-readable name for this rule type
    """

    rule_type: str = ""
    description: str = ""

    @abstractmethod
    async def check(
        self,
        db: AsyncSession,
        host: Host,
        rule: AlertRule,
        now: datetime,
    ) -> dict | None:
        """Return alert kwargs dict if threshold exceeded, else None.

        Expected keys in return dict:
            title: str
            description: str
            confidence: float (optional)
            mitre_technique_id: str (optional)
            mitre_tactic: str (optional)
        """
        ...


# Registry: rule_type string -> checker instance
_CHECKER_REGISTRY: dict[str, RuleChecker] = {}


def register_checker(checker: RuleChecker) -> RuleChecker:
    """Register a rule checker. Called at module load time."""
    _CHECKER_REGISTRY[checker.rule_type] = checker
    return checker


def get_checker(rule_type: str) -> RuleChecker | None:
    return _CHECKER_REGISTRY.get(rule_type)


def supported_rule_types() -> frozenset[str]:
    return frozenset(_CHECKER_REGISTRY.keys())


# Backward compatibility — old code imports SUPPORTED_RULE_TYPES as a set-like object.
# dict.keys() is a dynamic view that updates as the registry changes.
SUPPORTED_RULE_TYPES = _CHECKER_REGISTRY.keys()


# ---------------------------------------------------------------------------
# Built-in checkers
# ---------------------------------------------------------------------------

@register_checker
class FailedLoginsChecker(RuleChecker):
    rule_type = "failed_logins"
    description = "Multiple failed SSH logins within a time window"

    async def check(self, db, host, rule, now):
        window = timedelta(minutes=rule.window_minutes or 5)
        since = now - window
        count = (
            await db.execute(
                select(func.count()).select_from(Event).where(
                    Event.host_id == host.id,
                    Event.event_type == "ssh_login_failure",
                    Event.timestamp >= since,
                )
            )
        ).scalar_one()
        if count >= (rule.threshold or 5):
            return {
                "title": "Multiple Failed Logins",
                "description": f"{count} failed SSH logins in {rule.window_minutes} minutes",
            }
        return None


@register_checker
class BruteForceChecker(RuleChecker):
    rule_type = "brute_force"
    description = "High volume of failed logins indicating brute force"

    async def check(self, db, host, rule, now):
        window = timedelta(minutes=rule.window_minutes or 5)
        since = now - window
        count = (
            await db.execute(
                select(func.count()).select_from(Event).where(
                    Event.host_id == host.id,
                    Event.event_type == "ssh_login_failure",
                    Event.timestamp >= since,
                )
            )
        ).scalar_one()
        if count >= (rule.threshold or 10):
            return {
                "title": "Brute Force Attempt",
                "description": f"{count} failed SSH logins detected",
                "mitre_technique_id": "T1110",
                "mitre_tactic": "credential-access",
            }
        return None


@register_checker
class HighCpuChecker(RuleChecker):
    rule_type = "high_cpu"
    description = "Sustained high CPU usage across multiple samples"

    async def check(self, db, host, rule, now):
        result = await db.execute(
            select(Metric)
            .where(Metric.host_id == host.id)
            .order_by(Metric.recorded_at.desc())
            .limit(3)
        )
        recent = list(result.scalars().all())
        if len(recent) < 3:
            return None
        threshold = rule.threshold or 90
        if all(m.cpu_percent and m.cpu_percent > threshold for m in recent[:3]):
            return {
                "title": "High CPU Usage",
                "description": f"CPU above {threshold}% for 3 consecutive samples",
            }
        return None


@register_checker
class HighMemoryChecker(RuleChecker):
    rule_type = "high_memory"
    description = "Memory usage above threshold"

    async def check(self, db, host, rule, now):
        result = await db.execute(
            select(Metric)
            .where(Metric.host_id == host.id)
            .order_by(Metric.recorded_at.desc())
            .limit(1)
        )
        latest = result.scalar_one_or_none()
        if not latest:
            return None
        threshold = rule.threshold or 90
        if latest.memory_percent and latest.memory_percent > threshold:
            return {
                "title": "High Memory Usage",
                "description": f"Memory at {latest.memory_percent:.1f}%",
            }
        return None


@register_checker
class HighDiskChecker(RuleChecker):
    rule_type = "high_disk"
    description = "Disk usage above threshold"

    async def check(self, db, host, rule, now):
        result = await db.execute(
            select(Metric)
            .where(Metric.host_id == host.id)
            .order_by(Metric.recorded_at.desc())
            .limit(1)
        )
        latest = result.scalar_one_or_none()
        if not latest:
            return None
        threshold = rule.threshold or 85
        if latest.disk_percent and latest.disk_percent > threshold:
            return {
                "title": "High Disk Usage",
                "description": f"Disk at {latest.disk_percent:.1f}%",
            }
        return None


@register_checker
class ServiceFailureChecker(RuleChecker):
    rule_type = "service_failure"
    description = "A systemd service reported failure"

    async def check(self, db, host, rule, now):
        # This checker is triggered per-event, not by polling.
        # The event_type "service_failure" triggers an immediate alert.
        return {
            "title": "Service Failure",
            "description": "A service failure was detected",
        }


@register_checker
class AgentOfflineChecker(RuleChecker):
    rule_type = "agent_offline"
    description = "Agent has not sent a heartbeat within threshold"

    async def check(self, db, host, rule, now):
        # This checker is triggered by update_host_statuses, not polling.
        # The staleness check happens there.
        return None


# ---------------------------------------------------------------------------
# Alert creation helper
# ---------------------------------------------------------------------------

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
    host = await db.get(Host, host_id)
    from app.search.indexer import index_alert
    await index_alert(alert, host.name if host else "")

    from app.services.in_app_notifications import record_in_app_notification
    await record_in_app_notification(
        db, kind="alert", title=title, body=description,
        severity=severity, resource_type="alert", resource_id=alert.id,
    )

    from app.services.offense_engine import process_new_alert
    await process_new_alert(db, alert)

    from app.jobs.queue import job_queue
    await job_queue.enqueue("notify_alert", {"alert_id": str(alert.id)})

    from app.services.playbooks import schedule_playbook_dispatch
    await schedule_playbook_dispatch("alert_created", "alert", alert.id)

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


# ---------------------------------------------------------------------------
# Engine core
# ---------------------------------------------------------------------------

async def seed_alert_rules(db: AsyncSession) -> None:
    """Seed default alert rules if none exist."""
    result = await db.execute(select(func.count()).select_from(AlertRule))
    if result.scalar_one() > 0:
        return

    defaults = [
        {"name": "Failed Logins", "rule_type": "failed_logins", "threshold": 5, "window_minutes": 5, "severity": "high"},
        {"name": "Brute Force", "rule_type": "brute_force", "threshold": 10, "window_minutes": 5, "severity": "critical"},
        {"name": "High CPU", "rule_type": "high_cpu", "threshold": 90, "window_minutes": 2, "severity": "medium"},
        {"name": "High Memory", "rule_type": "high_memory", "threshold": 90, "window_minutes": 1, "severity": "medium"},
        {"name": "High Disk", "rule_type": "high_disk", "threshold": 85, "window_minutes": 1, "severity": "high"},
        {"name": "Service Failure", "rule_type": "service_failure", "threshold": 1, "window_minutes": 1, "severity": "high"},
        {"name": "Agent Offline", "rule_type": "agent_offline", "threshold": 90, "window_minutes": 1, "severity": "critical"},
    ]
    for rule in defaults:
        db.add(AlertRule(**rule))


async def run_detection_for_host(db: AsyncSession, host: Host) -> None:
    """Run all enabled detection rules against a host.

    This is the engine loop. It iterates over enabled rules, looks up
    the appropriate checker from the registry, and calls check().
    No hardcoded if/else — new rule types are added by registering a checker.
    """
    in_maint = await is_host_in_maintenance(db, host.id)
    if in_maint:
        return

    rules_result = await db.execute(
        select(AlertRule).where(AlertRule.enabled.is_(True))
    )
    rules = rules_result.scalars().all()
    now = datetime.now(timezone.utc)

    for rule in rules:
        checker = get_checker(rule.rule_type)
        if checker is None:
            logger.warning("No checker registered for rule_type=%s", rule.rule_type)
            continue
        try:
            result = await checker.check(db, host, rule, now)
        except Exception:
            logger.exception("Checker %s failed for host %s", rule.rule_type, host.id)
            continue
        if result is None:
            continue
        await create_alert(
            db,
            host.id,
            result["title"],
            result["description"],
            rule.severity,
            rule.id,
            confidence=result.get("confidence"),
            mitre_technique_id=result.get("mitre_technique_id"),
            mitre_tactic=result.get("mitre_tactic"),
        )


async def check_service_failure_event(db: AsyncSession, host: Host, event_type: str) -> None:
    """Triggered when a service_failure event is ingested."""
    if event_type != "service_failure":
        return
    rules_result = await db.execute(
        select(AlertRule).where(AlertRule.rule_type == "service_failure")
    )
    rule = rules_result.scalar_one_or_none()
    if rule:
        await create_alert(db, host.id, "Service Failure", "A service failure was detected", rule.severity, rule.id)


async def update_host_statuses(db: AsyncSession) -> None:
    """Update host status based on heartbeats and open alerts."""
    now = datetime.now(timezone.utc)
    hosts_result = await db.execute(select(Host))
    hosts = hosts_result.scalars().all()

    for host in hosts:
        old_status = host.status

        if not host.api_key_hash:
            if host.status != "inactive":
                host.status = "inactive"
                await ws_manager.broadcast({
                    "type": "host_status",
                    "data": {"id": str(host.id), "status": host.status, "name": host.name, "enrolled": False},
                })
            continue

        open_alerts = await db.execute(
            select(Alert).where(Alert.host_id == host.id, Alert.status == "open")
        )
        alerts = list(open_alerts.scalars().all())
        critical_alerts = [a for a in alerts if a.severity == "critical"]
        high_alerts = [a for a in alerts if a.severity in ("high", "medium")]

        stale = not host.last_seen or (now - host.last_seen).total_seconds() > 90

        if critical_alerts:
            host.status = "critical"
        elif stale:
            host.status = "offline"
            rules_result = await db.execute(
                select(AlertRule).where(AlertRule.rule_type == "agent_offline")
            )
            offline_rule = rules_result.scalar_one_or_none()
            open_rule_ids = {a.rule_id for a in alerts if a.rule_id}
            if offline_rule and offline_rule.id not in open_rule_ids:
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
