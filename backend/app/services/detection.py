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

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession


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


def register_checker(checker_cls: type[RuleChecker]) -> type[RuleChecker]:
    """Register a rule checker instance. Called at module load time."""
    _CHECKER_REGISTRY[checker_cls.rule_type] = checker_cls()
    return checker_cls


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
        window = timedelta(minutes=rule.window_minutes or 15)
        since = now - window
        count = (
            await db.execute(
                select(func.count()).select_from(Event).where(
                    Event.host_id == host.id,
                    Event.event_type == "service_failure",
                    Event.timestamp >= since,
                )
            )
        ).scalar_one()
        if count >= (rule.threshold or 1):
            return {
                "title": "Service Failure",
                "description": f"{count} service failure event(s) in {rule.window_minutes} minutes on {host.name}",
            }
        return None


@register_checker
class AgentOfflineChecker(RuleChecker):
    rule_type = "agent_offline"
    description = "Agent has not sent a heartbeat within threshold"

    async def check(self, db, host, rule, now):
        # This checker is triggered by update_host_statuses, not polling.
        # The staleness check happens there.
        return None


@register_checker
class PrivilegeEscalationChecker(RuleChecker):
    rule_type = "privilege_escalation"
    description = "Sudo or privilege escalation activity detected"

    async def check(self, db, host, rule, now):
        window = timedelta(minutes=rule.window_minutes or 5)
        since = now - window
        count = (
            await db.execute(
                select(func.count()).select_from(Event).where(
                    Event.host_id == host.id,
                    Event.event_type == "sudo_usage",
                    Event.timestamp >= since,
                )
            )
        ).scalar_one()
        if count >= (rule.threshold or 3):
            return {
                "title": "Privilege Escalation Detected",
                "description": f"{count} sudo invocations in {rule.window_minutes} minutes on {host.name}",
                "mitre_technique_id": "T1548.003",
                "mitre_tactic": "privilege-escalation",
                "confidence": 0.9,
            }
        return None


@register_checker
class RootLoginChecker(RuleChecker):
    rule_type = "root_login"
    description = "Direct root login detected"

    async def check(self, db, host, rule, now):
        window = timedelta(minutes=rule.window_minutes or 15)
        since = now - window
        count = (
            await db.execute(
                select(func.count()).select_from(Event).where(
                    Event.host_id == host.id,
                    Event.event_type == "root_login",
                    Event.timestamp >= since,
                )
            )
        ).scalar_one()
        if count >= (rule.threshold or 1):
            return {
                "title": "Direct Root Login Detected",
                "description": f"Root login detected on {host.name} — investigate immediately",
                "mitre_technique_id": "T1078.003",
                "mitre_tactic": "initial-access",
                "confidence": 0.95,
            }
        return None


@register_checker
class SuccessfulSSHAfterFailuresChecker(RuleChecker):
    rule_type = "ssh_success_after_failures"
    description = "Successful SSH login after multiple failures — likely compromised account"

    async def check(self, db, host, rule, now):
        window = timedelta(minutes=rule.window_minutes or 10)
        since = now - window

        fail_count = (
            await db.execute(
                select(func.count()).select_from(Event).where(
                    Event.host_id == host.id,
                    Event.event_type == "ssh_login_failure",
                    Event.timestamp >= since,
                )
            )
        ).scalar_one()

        if fail_count < (rule.threshold or 5):
            return None

        # Check if there was a successful login AFTER the failures
        success = (
            await db.execute(
                select(Event).where(
                    Event.host_id == host.id,
                    Event.event_type == "ssh_login_success",
                    Event.timestamp >= since,
                ).order_by(Event.timestamp.desc()).limit(1)
            )
        ).scalar_one_or_none()

        if success:
            return {
                "title": "Compromised Account — SSH Success After Failures",
                "description": f"{fail_count} failed attempts followed by successful login on {host.name}",
                "mitre_technique_id": "T1110",
                "mitre_tactic": "credential-access",
                "confidence": 0.85,
            }
        return None


@register_checker
class ServiceStopChecker(RuleChecker):
    rule_type = "service_stop"
    description = "Critical service was stopped — possible attack or tampering"

    async def check(self, db, host, rule, now):
        window = timedelta(minutes=rule.window_minutes or 5)
        since = now - window
        count = (
            await db.execute(
                select(func.count()).select_from(Event).where(
                    Event.host_id == host.id,
                    Event.event_type == "service_stop",
                    Event.timestamp >= since,
                )
            )
        ).scalar_one()
        if count >= (rule.threshold or 1):
            return {
                "title": "Service Stopped Unexpectedly",
                "description": f"A service was stopped on {host.name} — possible tampering",
                "mitre_technique_id": "T1489",
                "mitre_tactic": "impact",
                "confidence": 0.7,
            }
        return None


@register_checker
class FileIntegrityChecker(RuleChecker):
    rule_type = "file_integrity"
    description = "Critical system file was modified"

    async def check(self, db, host, rule, now):
        window = timedelta(minutes=rule.window_minutes or 15)
        since = now - window
        count = (
            await db.execute(
                select(func.count()).select_from(Event).where(
                    Event.host_id == host.id,
                    Event.event_type == "file_change",
                    Event.timestamp >= since,
                )
            )
        ).scalar_one()
        if count >= (rule.threshold or 1):
            return {
                "title": "File Integrity Alert",
                "description": f"{count} critical file changes detected on {host.name}",
                "mitre_technique_id": "T1070.004",
                "mitre_tactic": "defense-evasion",
                "confidence": 0.8,
            }
        return None


@register_checker
class FirewallBlockChecker(RuleChecker):
    rule_type = "firewall_block"
    description = "Firewall blocked connection — possible scanning or attack"

    async def check(self, db, host, rule, now):
        window = timedelta(minutes=rule.window_minutes or 5)
        since = now - window
        count = (
            await db.execute(
                select(func.count()).select_from(Event).where(
                    Event.host_id == host.id,
                    Event.event_type == "firewall_block",
                    Event.timestamp >= since,
                )
            )
        ).scalar_one()
        if count >= (rule.threshold or 10):
            return {
                "title": "Firewall Block Surge",
                "description": f"{count} connections blocked by firewall on {host.name} in {rule.window_minutes} minutes",
                "mitre_technique_id": "T1046",
                "mitre_tactic": "discovery",
                "confidence": 0.75,
            }
        return None


@register_checker
class NetworkAnomalyChecker(RuleChecker):
    rule_type = "network_anomaly"
    description = "Abnormal network connection volume — possible C2 or exfiltration"

    async def check(self, db, host, rule, now):
        window = timedelta(minutes=rule.window_minutes or 5)
        since = now - window
        count = (
            await db.execute(
                select(func.count()).select_from(Event).where(
                    Event.host_id == host.id,
                    Event.event_type == "network_connection",
                    Event.timestamp >= since,
                )
            )
        ).scalar_one()
        if count >= (rule.threshold or 50):
            return {
                "title": "Abnormal Network Activity",
                "description": f"{count} network connections in {rule.window_minutes} minutes on {host.name} — possible C2 or exfiltration",
                "mitre_technique_id": "T1040",
                "mitre_tactic": "credential-access",
                "confidence": 0.7,
            }
        return None


# ---------------------------------------------------------------------------
# Alert creation helper
# ---------------------------------------------------------------------------

async def _recently_closed_rule_alert(
    db: AsyncSession,
    host_id,
    rule_id,
    cooldown_minutes: int,
) -> bool:
    """Suppress re-opening the same rule alert shortly after triage."""
    if cooldown_minutes <= 0:
        return False
    since = datetime.now(timezone.utc) - timedelta(minutes=cooldown_minutes)
    recent = (
        await db.execute(
            select(Alert.id)
            .where(
                Alert.host_id == host_id,
                Alert.rule_id == rule_id,
                Alert.status.in_(["resolved", "closed"]),
                Alert.resolved_at.is_not(None),
                Alert.resolved_at >= since,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    return recent is not None


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
    source: str | None = None,
    cooldown_minutes: int | None = None,
) -> Alert | None:
    if rule_id is not None and await _recently_closed_rule_alert(
        db, host_id, rule_id, cooldown_minutes if cooldown_minutes is not None else 15
    ):
        return None
    if rule_id is not None:
        stmt = (
            pg_insert(Alert)
            .values(
                host_id=host_id,
                rule_id=rule_id,
                source=source,
                severity=severity,
                title=title,
                description=description,
                status="open",
                confidence=confidence,
                mitre_technique_id=mitre_technique_id,
                mitre_tactic=mitre_tactic,
            )
            .on_conflict_do_nothing(
                index_elements=["host_id", "rule_id"],
                index_where=text("(status)::text = 'open' AND rule_id IS NOT NULL"),
            )
            .returning(Alert)
        )
    else:
        stmt = (
            pg_insert(Alert)
            .values(
                host_id=host_id,
                rule_id=None,
                source=source,
                severity=severity,
                title=title,
                description=description,
                status="open",
                confidence=confidence,
                mitre_technique_id=mitre_technique_id,
                mitre_tactic=mitre_tactic,
            )
            .on_conflict_do_nothing(
                index_elements=["host_id", "title"],
                index_where=text("(status)::text = 'open' AND rule_id IS NULL"),
            )
            .returning(Alert)
        )

    result = await db.execute(stmt)
    alert = result.scalar_one_or_none()
    if not alert:
        return None

    await db.flush()
    host = await db.get(Host, host_id)

    # Record side effects to execute after commit (outbox pattern)
    if "post_commit_hooks" not in db.info:
        db.info["post_commit_hooks"] = []
    hooks: list = db.info["post_commit_hooks"]

    # In-app notification must stay inside the transaction
    from app.services.in_app_notifications import record_in_app_notification
    await record_in_app_notification(
        db, kind="alert", title=title, body=description,
        severity=severity, resource_type="alert", resource_id=alert.id,
    )

    from app.services.offense_engine import process_new_alert
    await process_new_alert(db, alert)

    # These side effects execute after commit via the outbox
    hooks.append(lambda: _execute_alert_post_commit(alert, host, host_id, title, severity, confidence))

    return alert


async def _execute_alert_post_commit(alert, host, host_id, title, severity, confidence):
    """Run post-commit side effects for alert creation. Safe to fail — logged and retried."""
    try:
        from app.search.indexer import index_alert
        await index_alert(alert, host.name if host else "")
    except Exception:
        logger.warning("post-commit: index_alert failed for %s", alert.id, exc_info=True)

    try:
        from app.jobs.queue import job_queue
        await job_queue.enqueue("notify_alert", {"alert_id": str(alert.id)})
    except Exception:
        logger.warning("post-commit: notify_alert enqueue failed for %s", alert.id, exc_info=True)

    try:
        from app.services.playbooks import schedule_playbook_dispatch
        await schedule_playbook_dispatch("alert_created", "alert", alert.id)
    except Exception:
        logger.warning("post-commit: playbook_dispatch failed for %s", alert.id, exc_info=True)

    try:
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
    except Exception:
        logger.warning("post-commit: new_alert broadcast failed for %s", alert.id, exc_info=True)


# ---------------------------------------------------------------------------
# Engine core
# ---------------------------------------------------------------------------

async def seed_alert_rules(db: AsyncSession) -> None:
    """Seed default alert rules if none exist."""
    result = await db.execute(select(func.count()).select_from(AlertRule))
    if result.scalar_one() > 0:
        return

    defaults = [
        # ── Authentication & Access ──────────────────────────────────────
        {"name": "Failed Logins", "rule_type": "failed_logins", "threshold": 5, "window_minutes": 5, "severity": "high"},
        {"name": "Brute Force", "rule_type": "brute_force", "threshold": 10, "window_minutes": 5, "severity": "critical"},
        {"name": "SSH Success After Failures", "rule_type": "ssh_success_after_failures", "threshold": 5, "window_minutes": 10, "severity": "critical"},
        {"name": "Root Login Detected", "rule_type": "root_login", "threshold": 1, "window_minutes": 15, "severity": "critical"},
        {"name": "Privilege Escalation", "rule_type": "privilege_escalation", "threshold": 3, "window_minutes": 5, "severity": "critical"},
        # ── Host Health ──────────────────────────────────────────────────
        {"name": "High CPU", "rule_type": "high_cpu", "threshold": 90, "window_minutes": 2, "severity": "medium"},
        {"name": "High Memory", "rule_type": "high_memory", "threshold": 90, "window_minutes": 1, "severity": "medium"},
        {"name": "High Disk", "rule_type": "high_disk", "threshold": 85, "window_minutes": 1, "severity": "high"},
        # ── System Integrity ─────────────────────────────────────────────
        {"name": "Service Failure", "rule_type": "service_failure", "threshold": 1, "window_minutes": 1, "severity": "high"},
        {"name": "Service Stopped", "rule_type": "service_stop", "threshold": 1, "window_minutes": 5, "severity": "high"},
        {"name": "File Integrity Alert", "rule_type": "file_integrity", "threshold": 1, "window_minutes": 15, "severity": "high"},
        {"name": "Agent Offline", "rule_type": "agent_offline", "threshold": 90, "window_minutes": 1, "severity": "critical"},
        # ── Network & Perimeter ──────────────────────────────────────────
        {"name": "Firewall Block Surge", "rule_type": "firewall_block", "threshold": 10, "window_minutes": 5, "severity": "medium"},
        {"name": "Network Anomaly", "rule_type": "network_anomaly", "threshold": 50, "window_minutes": 5, "severity": "high"},
    ]
    for rule in defaults:
        db.add(AlertRule(**rule))


async def run_detection_for_host(db: AsyncSession, host: Host, source: str | None = None) -> None:
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
            source=source,
            cooldown_minutes=rule.window_minutes or 15,
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
        await create_alert(
            db,
            host.id,
            "Service Failure",
            "A service failure was detected",
            rule.severity,
            rule.id,
            cooldown_minutes=rule.window_minutes or 15,
        )


async def update_host_statuses(db: AsyncSession) -> None:
    """Update host status based on heartbeats and open alerts."""
    from collections import defaultdict

    now = datetime.now(timezone.utc)
    hosts_result = await db.execute(select(Host))
    hosts = hosts_result.scalars().all()

    if not hosts:
        return

    host_ids = [h.id for h in hosts]

    all_open_alerts = (
        await db.execute(
            select(Alert).where(Alert.host_id.in_(host_ids), Alert.status == "open")
        )
    ).scalars().all()

    alerts_by_host: dict = defaultdict(list)
    for alert in all_open_alerts:
        alerts_by_host[alert.host_id].append(alert)

    offline_rule = None
    hosts_with_api_key = [h for h in hosts if h.api_key_hash]
    if hosts_with_api_key:
        rules_result = await db.execute(
            select(AlertRule).where(AlertRule.rule_type == "agent_offline")
        )
        offline_rule = rules_result.scalar_one_or_none()

    maintenance_host_ids: set = set()
    if offline_rule:
        # Batch-load active maintenance windows for all hosts with API keys
        from app.models.maintenance import MaintenanceWindow
        now_maint = datetime.now(timezone.utc)
        maint_result = await db.execute(
            select(MaintenanceWindow.host_id).where(
                MaintenanceWindow.host_id.in_([h.id for h in hosts_with_api_key]),
                MaintenanceWindow.starts_at <= now_maint,
                MaintenanceWindow.ends_at >= now_maint,
            )
        )
        maintenance_host_ids = set(maint_result.scalars().all())

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

        alerts = alerts_by_host.get(host.id, [])
        critical_alerts = [a for a in alerts if a.severity == "critical"]
        high_alerts = [a for a in alerts if a.severity in ("high", "medium")]

        never_seen = host.last_seen is None
        stale = not never_seen and (now - host.last_seen).total_seconds() > 90

        if critical_alerts:
            host.status = "critical"
        elif never_seen:
            host.status = "inactive"
        elif stale:
            host.status = "offline"
            open_rule_ids = {a.rule_id for a in alerts if a.rule_id}
            if offline_rule and offline_rule.id not in open_rule_ids:
                if host.id not in maintenance_host_ids:
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
