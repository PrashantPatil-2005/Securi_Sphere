"""QRadar-style offense grouping with related entities and timeline."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.event import Event
from app.models.siem import Offense, OffenseEvent

OFFENSE_WINDOW = timedelta(minutes=30)

RISK_FROM_SEVERITY = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
    "info": "low",
}

RISK_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}

AUTH_EVENT_TYPES = frozenset({
    "ssh_login_failure", "ssh_login_success", "sudo_usage", "root_login",
})


async def _next_offense_number(db: AsyncSession) -> int:
    current = (await db.execute(select(func.max(Offense.offense_number)))).scalar_one()
    return (current or 100) + 1


def _max_risk(a: str, b: str) -> str:
    return a if RISK_RANK.get(a, 0) >= RISK_RANK.get(b, 0) else b


def _append_timeline_entry(offense: Offense, entry: dict) -> None:
    timeline = list(offense.timeline or [])
    timeline.append(entry)
    timeline.sort(key=lambda x: x.get("timestamp", ""))
    offense.timeline = timeline[-500:]


def _track_user(offense: Offense, username: str | None) -> None:
    if not username:
        return
    users = list(offense.related_users or [])
    if username not in users:
        users.append(username)
        offense.related_users = users


async def find_or_create_offense(
    db: AsyncSession,
    host_id: UUID,
    title: str,
    risk_level: str = "medium",
) -> tuple[Offense, bool]:
    since = datetime.now(timezone.utc) - OFFENSE_WINDOW
    existing = (
        await db.execute(
            select(Offense)
            .where(
                Offense.host_id == host_id,
                Offense.status.in_(["open", "investigating"]),
                Offense.updated_at >= since,
            )
            .order_by(Offense.updated_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if existing:
        existing.updated_at = datetime.now(timezone.utc)
        existing.risk_level = _max_risk(existing.risk_level, risk_level)
        return existing, False

    offense = Offense(
        offense_number=await _next_offense_number(db),
        host_id=host_id,
        title=title,
        description="Correlated security activity on host",
        risk_level=risk_level,
        status="open",
        event_count=0,
        alert_count=0,
        related_hosts=[str(host_id)],
        related_users=[],
        timeline=[],
    )
    db.add(offense)
    await db.flush()
    from app.services.in_app_notifications import record_in_app_notification

    await record_in_app_notification(
        db,
        kind="offense",
        title=f"Offense #{offense.offense_number}: {title}",
        body=offense.description,
        severity=risk_level,
        resource_type="offense",
        resource_id=offense.id,
    )
    if risk_level in ("critical", "high"):
        from app.jobs.queue import job_queue
        await job_queue.enqueue("notify_offense", {"offense_id": str(offense.id)})
    from app.services.playbooks import schedule_playbook_dispatch
    await schedule_playbook_dispatch("offense_created", "offense", offense.id)
    return offense, True


async def link_alert_to_offense(db: AsyncSession, alert: Alert) -> Offense:
    offense, _created = await find_or_create_offense(
        db,
        alert.host_id,
        title=alert.title,
        risk_level=RISK_FROM_SEVERITY.get(alert.severity, "medium"),
    )

    dup = (
        await db.execute(
            select(OffenseEvent).where(
                OffenseEvent.offense_id == offense.id, OffenseEvent.alert_id == alert.id
            )
        )
    ).scalar_one_or_none()
    if not dup:
        db.add(OffenseEvent(offense_id=offense.id, alert_id=alert.id))
        offense.alert_count += 1
        offense.event_count += 1
        offense.updated_at = datetime.now(timezone.utc)
        _append_timeline_entry(offense, {
            "type": "alert",
            "id": str(alert.id),
            "title": alert.title,
            "severity": alert.severity,
            "timestamp": alert.created_at.isoformat() if alert.created_at else datetime.now(timezone.utc).isoformat(),
        })

    hosts = list(offense.related_hosts or [])
    host_str = str(alert.host_id)
    if host_str not in hosts:
        hosts.append(host_str)
        offense.related_hosts = hosts

    return offense


async def link_event_to_offense(db: AsyncSession, event: Event) -> Offense | None:
    if event.event_type not in AUTH_EVENT_TYPES and event.event_type not in (
        "service_failure", "service_stop", "agent_disconnect",
    ):
        return None

    risk = "high" if event.event_type in ("ssh_login_failure", "root_login", "service_stop") else "medium"
    offense, _created = await find_or_create_offense(
        db,
        event.host_id,
        title=f"Security activity: {event.event_type}",
        risk_level=risk,
    )

    dup = (
        await db.execute(
            select(OffenseEvent).where(
                OffenseEvent.offense_id == offense.id, OffenseEvent.event_id == event.id
            )
        )
    ).scalar_one_or_none()
    if not dup:
        db.add(OffenseEvent(offense_id=offense.id, event_id=event.id))
        offense.event_count += 1
        offense.updated_at = datetime.now(timezone.utc)
        _append_timeline_entry(offense, {
            "type": "event",
            "id": str(event.id),
            "event_type": event.event_type,
            "severity": event.severity,
            "username": event.username,
            "source_ip": str(event.source_ip) if event.source_ip else None,
            "timestamp": event.timestamp.isoformat(),
        })
        _track_user(offense, event.username)

    return offense


async def process_new_alert(db: AsyncSession, alert: Alert) -> Offense:
    return await link_alert_to_offense(db, alert)


async def get_offense_summary(db: AsyncSession, offense_id: UUID) -> dict | None:
    offense = await db.get(Offense, offense_id)
    if not offense:
        return None
    links = (
        await db.execute(select(OffenseEvent).where(OffenseEvent.offense_id == offense.id))
    ).scalars().all()
    alert_ids = [l.alert_id for l in links if l.alert_id]
    event_ids = [l.event_id for l in links if l.event_id]
    return {
        "offense": offense,
        "alert_ids": alert_ids,
        "event_ids": event_ids,
        "related_hosts": offense.related_hosts,
        "related_users": offense.related_users,
        "timeline": offense.timeline,
    }
