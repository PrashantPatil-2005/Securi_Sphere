"""Correlation engine — evaluates event sequences against rules.

The correlation engine runs after detection. It looks at sequences of events
(rather than individual events) to detect attack patterns that single-alert
rules would miss.

Three matcher algorithms (see correlation/framework.py for details):
1. SequenceMatcher: ordered events within a time window
2. CoOccurrenceMatcher: related events appearing together
3. CrossHostMatcher: same attacker across multiple hosts

The engine evaluates all enabled rules against recent events for a host.
When a rule fires, it creates a CorrelationResult with confidence score
and optionally generates an alert.

Confidence scoring is heuristic-based (not ML). Scores range 0-100 and
are computed from:
- Base confidence defined in the rule
- Bonus for high-severity event combinations
- Bonus for compressed attack timelines
- Bonus for cross-host impact
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.correlation import CorrelationResult, CorrelationRule
from app.models.event import Event
from app.services.correlation.framework import MATCHERS, CoOccurrenceMatcher, SequenceMatcher
from app.services.correlation.rules import CO_OCCURRENCE_RULES, CROSS_HOST_RULES, DEFAULT_CORRELATION_RULES


def _matcher_for_rule(rule: CorrelationRule):
    desc = rule.description or ""
    if desc.startswith("[cross_host]"):
        return MATCHERS["cross_host"]
    if desc.startswith("[co_occurrence]"):
        return MATCHERS["co_occurrence"]
    return MATCHERS["sequence"]


async def seed_correlation_rules(db: AsyncSession) -> None:
    from sqlalchemy import func

    if (await db.execute(select(func.count()).select_from(CorrelationRule))).scalar_one() > 0:
        existing_names = set(
            (await db.execute(select(CorrelationRule.name))).scalars().all()
        )
        for rule in CROSS_HOST_RULES:
            if rule["name"] not in existing_names:
                db.add(CorrelationRule(**rule))
        return
    for rule in DEFAULT_CORRELATION_RULES + CO_OCCURRENCE_RULES + CROSS_HOST_RULES:
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


async def run_cross_host_correlation(db: AsyncSession) -> list[CorrelationResult]:
    """Evaluate cross-host rules against recent events cluster-wide."""
    from app.services.detection import create_alert

    results: list[CorrelationResult] = []
    rules = (
        await db.execute(
            select(CorrelationRule).where(
                CorrelationRule.enabled.is_(True),
                CorrelationRule.description.like("[cross_host]%"),
            )
        )
    ).scalars().all()
    if not rules:
        return results

    max_window = max((r.window_minutes or 10 for r in rules), default=10)
    since = datetime.now(timezone.utc) - timedelta(minutes=max_window)
    events = (
        await db.execute(select(Event).where(Event.timestamp >= since).order_by(Event.timestamp))
    ).scalars().all()

    for rule in rules:
        matcher = MATCHERS["cross_host"]
        matched = matcher.matches(list(events), rule)
        if not matched:
            continue
        confidence = matcher.score(matched, rule)
        primary_host = matched[0].host_id
        existing = (
            await db.execute(
                select(CorrelationResult).where(
                    CorrelationResult.rule_id == rule.id,
                    CorrelationResult.detected_at >= since,
                )
            )
        ).scalar_one_or_none()
        if existing:
            continue
        alert = await create_alert(
            db,
            primary_host,
            rule.name,
            rule.description or f"Cross-host correlation: {rule.name}",
            rule.severity,
            None,
            confidence=confidence,
        )
        result = CorrelationResult(
            rule_id=rule.id,
            host_id=primary_host,
            event_ids=[str(e.id) for e in matched],
            confidence=confidence,
            alert_id=alert.id if alert else None,
        )
        db.add(result)
        results.append(result)
    return results
