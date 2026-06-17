from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.correlation import CorrelationResult, CorrelationRule
from app.models.event import Event

ATTACK_EVENTS = {
    "ssh_login_failure", "ssh_login_success", "root_login", "sudo_usage", "service_failure",
}

DEFAULT_CORRELATION_RULES = [
    {
        "name": "Brute Force to Privilege Escalation",
        "description": "Failed logins followed by success and sudo usage",
        "event_sequence": ["ssh_login_failure", "ssh_login_success", "sudo_usage"],
        "window_minutes": 20,
        "min_occurrences": {"ssh_login_failure": 3},
        "severity": "critical",
        "confidence_base": 0.75,
        "is_system": True,
    },
    {
        "name": "Suspicious Login After Failures",
        "description": "Successful login after multiple failed attempts",
        "event_sequence": ["ssh_login_failure", "ssh_login_success"],
        "window_minutes": 15,
        "min_occurrences": {"ssh_login_failure": 3},
        "severity": "high",
        "confidence_base": 0.65,
        "is_system": True,
    },
]


async def seed_correlation_rules(db: AsyncSession) -> None:
    from sqlalchemy import func

    if (await db.execute(select(func.count()).select_from(CorrelationRule))).scalar_one() > 0:
        return
    for rule in DEFAULT_CORRELATION_RULES:
        db.add(CorrelationRule(**rule))


def _score_match(events: list[Event], rule: CorrelationRule) -> float:
    base = (rule.confidence_base or 0.5) * 100
    types = [e.event_type for e in events]
    if "sudo_usage" in types and "ssh_login_success" in types:
        base += 15
    if types.count("ssh_login_failure") >= 5:
        base += 10
    if len(events) >= 2:
        span = (events[-1].timestamp - events[0].timestamp).total_seconds()
        if span < 600:
            base += 10
    return min(base, 100)


def _sequence_matches(events: list[Event], rule: CorrelationRule) -> list[Event] | None:
    window = timedelta(minutes=rule.window_minutes or 20)
    now = datetime.now(timezone.utc)
    recent = [e for e in events if e.timestamp >= now - window]
    recent.sort(key=lambda x: x.timestamp)

    for etype, min_count in (rule.min_occurrences or {}).items():
        if sum(1 for e in recent if e.event_type == etype) < min_count:
            return None

    seq = rule.event_sequence or []
    if not seq:
        return recent if recent else None

    found_idx = 0
    matched: list[Event] = []
    for event in recent:
        if event.event_type == seq[found_idx]:
            matched.append(event)
            found_idx += 1
            if found_idx >= len(seq):
                return matched
    return None


async def run_correlation_engine(db: AsyncSession, host_id) -> list[CorrelationResult]:
    from app.services.detection import create_alert

    results: list[CorrelationResult] = []
    rules = (await db.execute(select(CorrelationRule).where(CorrelationRule.enabled.is_(True)))).scalars().all()
    max_window = max((r.window_minutes or 20 for r in rules), default=30)
    since = datetime.now(timezone.utc) - timedelta(minutes=max_window)
    events = (
        await db.execute(
            select(Event).where(Event.host_id == host_id, Event.timestamp >= since).order_by(Event.timestamp)
        )
    ).scalars().all()

    for rule in rules:
        matched = _sequence_matches(list(events), rule)
        if not matched:
            continue
        confidence = _score_match(matched, rule)
        existing = (
            await db.execute(
                select(CorrelationResult).where(
                    CorrelationResult.rule_id == rule.id,
                    CorrelationResult.host_id == host_id,
                    CorrelationResult.detected_at >= since,
                )
            )
        ).scalar_one_or_none()
        if existing:
            continue

        alert = await create_alert(
            db,
            host_id,
            rule.name,
            rule.description or f"Correlation rule matched: {rule.name}",
            rule.severity,
            None,
            confidence=confidence,
        )
        result = CorrelationResult(
            rule_id=rule.id,
            host_id=host_id,
            event_ids=[str(e.id) for e in matched],
            confidence=confidence,
            alert_id=alert.id if alert else None,
        )
        db.add(result)
        results.append(result)
    return results
