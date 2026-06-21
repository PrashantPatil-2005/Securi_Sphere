from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.correlation import CorrelationResult, CorrelationRule
from app.models.event import Event
from app.services.correlation.framework import MATCHERS, CoOccurrenceMatcher, SequenceMatcher
from app.services.correlation.rules import CO_OCCURRENCE_RULES, DEFAULT_CORRELATION_RULES


def _matcher_for_rule(rule: CorrelationRule):
    if rule.description and rule.description.startswith("[co_occurrence]"):
        return MATCHERS["co_occurrence"]
    if len(rule.event_sequence or []) >= 2 and not rule.min_occurrences:
        types = rule.event_sequence or []
        if types != sorted(types, key=lambda t: t):
            pass
    return MATCHERS["sequence"]


async def seed_correlation_rules(db: AsyncSession) -> None:
    from sqlalchemy import func

    if (await db.execute(select(func.count()).select_from(CorrelationRule))).scalar_one() > 0:
        return
    for rule in DEFAULT_CORRELATION_RULES + CO_OCCURRENCE_RULES:
        db.add(CorrelationRule(**rule))


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
        matcher = _matcher_for_rule(rule)
        matched = matcher.matches(list(events), rule)
        if not matched:
            continue
        confidence = matcher.score(matched, rule)
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
