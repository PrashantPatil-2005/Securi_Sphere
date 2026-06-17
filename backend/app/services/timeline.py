from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.timeline import AttackTimeline
from app.services.mitre import EVENT_MITRE_MAP

ATTACK_EVENT_TYPES = set(EVENT_MITRE_MAP.keys())


async def build_timelines(db: AsyncSession, host_id, window_minutes: int = 60) -> list[AttackTimeline]:
    since = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    events = (
        await db.execute(
            select(Event)
            .where(Event.host_id == host_id, Event.timestamp >= since, Event.event_type.in_(ATTACK_EVENT_TYPES))
            .order_by(Event.timestamp)
        )
    ).scalars().all()

    if len(events) < 2:
        return []

    chain = list(events)
    started = chain[0].timestamp
    ended = chain[-1].timestamp
    techniques = list({e.mitre_technique_id for e in chain if e.mitre_technique_id})

    title = _chain_title([e.event_type for e in chain])
    confidence = _chain_confidence(chain)

    timeline = AttackTimeline(
        host_id=host_id,
        title=title,
        description=f"{len(chain)} correlated security events detected",
        started_at=started,
        ended_at=ended,
        event_ids=[str(e.id) for e in chain],
        mitre_techniques=techniques,
        severity="critical" if confidence >= 80 else "high" if confidence >= 60 else "medium",
        confidence=confidence,
        status="active",
    )
    db.add(timeline)
    return [timeline]


def _chain_title(types: list[str]) -> str:
    if "ssh_login_failure" in types and "ssh_login_success" in types and "sudo_usage" in types:
        return "Potential Attack Chain: Brute Force → Access → Escalation"
    if "ssh_login_failure" in types and "ssh_login_success" in types:
        return "Potential Attack Chain: Brute Force → Successful Login"
    if types.count("ssh_login_failure") >= 3:
        return "Potential Brute Force Activity"
    return "Suspicious Activity Sequence"


def _chain_confidence(events: list[Event]) -> float:
    score = 30.0
    types = [e.event_type for e in events]
    score += min(types.count("ssh_login_failure") * 5, 25)
    if "ssh_login_success" in types:
        score += 20
    if "sudo_usage" in types or "root_login" in types:
        score += 15
    if len(events) >= 2:
        span = (events[-1].timestamp - events[0].timestamp).total_seconds()
        if span < 900:
            score += 10
    return min(score, 100)


async def get_timelines(db: AsyncSession, host_id=None, limit: int = 50) -> list[AttackTimeline]:
    q = select(AttackTimeline).order_by(AttackTimeline.created_at.desc()).limit(limit)
    if host_id:
        q = q.where(AttackTimeline.host_id == host_id)
    return list((await db.execute(q)).scalars().all())
