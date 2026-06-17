"""QRadar-style offense grouping — correlates related alerts and events on a host."""
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


async def _next_offense_number(db: AsyncSession) -> int:
    current = (await db.execute(select(func.max(Offense.offense_number)))).scalar_one()
    return (current or 100) + 1


def _max_risk(a: str, b: str) -> str:
    return a if RISK_RANK.get(a, 0) >= RISK_RANK.get(b, 0) else b


async def find_or_create_offense(
    db: AsyncSession,
    host_id: UUID,
    title: str,
    risk_level: str = "medium",
) -> Offense:
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
        return existing

    offense = Offense(
        offense_number=await _next_offense_number(db),
        host_id=host_id,
        title=title,
        description=f"Correlated security activity on host",
        risk_level=risk_level,
        status="open",
        event_count=0,
    )
    db.add(offense)
    await db.flush()
    return offense


async def link_alert_to_offense(db: AsyncSession, alert: Alert) -> Offense:
    offense = await find_or_create_offense(
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
        offense.event_count += 1
        offense.updated_at = datetime.now(timezone.utc)
    return offense


async def link_event_to_offense(db: AsyncSession, event: Event) -> Offense | None:
    if event.event_type not in ("ssh_login_failure", "ssh_login_success", "sudo_usage", "root_login"):
        return None

    risk = "high" if event.event_type in ("ssh_login_failure", "root_login") else "medium"
    offense = await find_or_create_offense(
        db,
        event.host_id,
        title=f"Authentication activity: {event.event_type}",
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
    return offense


async def process_new_alert(db: AsyncSession, alert: Alert) -> Offense:
    return await link_alert_to_offense(db, alert)
