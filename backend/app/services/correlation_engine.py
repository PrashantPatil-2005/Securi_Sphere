"""Correlation engine — evaluates event sequences against rules and creates incidents.

The correlation engine runs after detection. It looks at sequences of events
(rather than individual events) to detect attack patterns that single-alert
rules would miss. When a significant attack chain is detected, an Incident
is created to support investigation and incident lifecycle tracking.

Three matcher algorithms (see correlation/framework.py for details):
1. SequenceMatcher: ordered events within a time window
2. CoOccurrenceMatcher: related events appearing together
3. CrossHostMatcher: same attacker across multiple hosts
"""

import uuid as uuid_module
from datetime import datetime, timedelta, timezone
from uuid import UUID

import logging

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.correlation import CorrelationResult, CorrelationRule
from app.models.event import Event
from app.models.incident import Incident
from app.services.correlation.framework import MATCHERS, build_correlation_match
from app.services.correlation.validation import rule_type_from_description
from app.services.detection import create_alert
from app.services.offense_engine import link_event_to_offense

logger = logging.getLogger(__name__)


def _incident_title_from_rule(rule: CorrelationRule, match: object) -> str:
    """Generate a human-readable incident title from a correlation rule and match."""
    base = rule.name or "Correlation Alert"
    if hasattr(match, "evidence") and match.evidence:
        agg = match.evidence.get("aggregated_mitre", {})
        techniques = agg.get("technique_ids", [])
        if techniques:
            return f"{base} — MITRE: {', '.join(techniques[:3])}"
    return base


def _incident_description_from_match(
    rule: CorrelationRule, match: object, events: list[Event]
) -> str:
    """Generate an evidence-backed incident description from a correlation match."""
    parts: list[str] = []
    if hasattr(match, "evidence") and match.evidence:
        ev = match.evidence
        # Time span
        ts = ev.get("time_span", {})
        duration = ts.get("duration_minutes")
        if duration is not None:
            parts.append(f"correlation window of {duration} minutes")
        # Involved hosts
        hosts = ev.get("involved_hosts", [])
        if hosts:
            parts.append(f"on {len(hosts)} host{'s' if len(hosts) > 1 else ''}")
        # Involved users
        users = ev.get("involved_users", [])
        if users:
            parts.append(f"involving user{'s' if len(users) > 1 else ''} {', '.join(users)}")
        # Docker service identity
        docker_ids = ev.get("docker_service_ids")
        if docker_ids:
            parts.append(f"Docker service: {docker_ids[0]}")
        # Aggregated MITRE
        mitre = agg = ev.get("aggregated_mitre", {})
        tids = agg.get("technique_ids", []) if agg else []
        if tids:
            parts.append(f"MITRE techniques: {', '.join(tids[:3])}")

    # Fallback: count events
    if not parts:
        parts.append(f"{len(events)} correlated event{'s' if len(events) > 1 else ''}")

    return " | ".join(parts)


# ---------------------------------------------------------------------------
# Incident creation from correlation
# ---------------------------------------------------------------------------

async def _create_incident_from_correlation(
    db: AsyncSession,
    host: object,
    rule: CorrelationRule,
    match: object,
    events: list[Event],
    source: str | None = "correlation",
) -> Incident | None:
    """Create an Incident from a correlation match, if evidence is sufficient."""

    # Minimum event threshold — skip if too few events to form an incident
    if len(events) < 2:
        return None

    # Aggregate MITRE and entity tracking
    mitre = match.evidence.get("aggregated_mitre", {}) if hasattr(match, "evidence") else {}
    technique_ids: list[str] = mitre.get("technique_ids", []) or []
    tactics: list[str] = mitre.get("tactics", []) or []

    # Collect affected hosts, users, services, containers from evidence
    evidence = match.evidence if hasattr(match, "evidence") else {}
    involved_hosts = evidence.get("involved_hosts", []) or []
    involved_users = evidence.get("involved_users", []) or []
    involved_source_ips = evidence.get("involved_source_ips", []) or []
    docker_service_ids = evidence.get("docker_service_ids", []) or []
    time_span = evidence.get("time_span", {}) or {}

    # Build incident title and description
    title = _incident_title_from_rule(rule, match)
    description = _incident_description_from_match(rule, match, events)

    # Compute first_observed / last_observed from event timestamps
    observed_times = [e.timestamp for e in events if e.timestamp]
    first_observed: datetime | None = None
    last_observed: datetime | None = None
    if observed_times:
        sorted_times = sorted(observed_times)
        first_observed = sorted_times[0]
        last_observed = sorted_times[-1]

    # Determine severity from rule severity
    severity = rule.severity or "medium"

    # Build incident data
    incident_data = {
        "title": title,
        "description": description,
        "severity": severity,
        "status": "open",
        "host_id": host.id if hasattr(host, "id") else None,
        "created_by": getattr(host, "id", None),  # will be overridden by actual user
        "first_observed": first_observed,
        "last_observed": last_observed,
        "affected_hosts": involved_hosts if involved_hosts else [str(host.id) if hasattr(host, "id") else None],
        "affected_users": involved_users,
        "affected_services": evidence.get("docker_service_ids", []),
        "affected_containers": [],  # populated later if container metadata available
        "mitre_technique_ids": technique_ids,
        "mitre_tactics": tactics,
        "confidence": match.confidence if match.confidence else 0.5,
    }

    # Check for existing open incident with same title+host to prevent duplicates
    from sqlalchemy import func as sa_func
    stmt = (
        select(Incident)
        .where(Incident.title == title)
        .where(Incident.host_id == incident_data["host_id"])
        .where(Incident.status.in_(["open", "investigating"]))
        .limit(1)
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        # Update existing incident's last_observed and timeline
        existing.last_observed = max(
            existing.last_observed or first_observed or datetime.now(timezone.utc),
            last_observed or datetime.now(timezone.utc),
        )
        if technique_ids:
            existing.mitre_technique_ids = sorted(
                set(existing.mitre_technique_ids or []) | set(technique_ids)
            )
        if tactics:
            existing.mitre_tactics = sorted(
                set(existing.mitre_tactics or []) | set(tactics)
            )
        # Update last_observed again
        existing.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return existing

    # Create new incident
    incident = Incident(**incident_data)
    db.add(incident)
    await db.flush()

    # Link related events to the incident via OffenseEvent pathway
    for event in events[:20]:  # limit to first 20 events to avoid bloat
        try:
            await link_event_to_offense(db, event)
        except Exception:
            logger_exception_msg = ""
            pass

    # Post-commit: broadcast new incident via WebSocket
    # (handled by the outbox pattern in create_alert / offense engine)

    await db.flush()
    return incident


# ---------------------------------------------------------------------------
# Engine core
# ---------------------------------------------------------------------------

async def run_correlation_engine(db: AsyncSession, host_id: UUID, source: str | None = "host_scan") -> list[CorrelationResult]:
    """Run all enabled correlation rules against a host and create incidents where evidence is sufficient.

    Returns list of CorrelationResult objects, with incidents created as a side effect
    for any rule that fires with sufficient evidence.
    """

    from app.services.host_notify import is_host_in_maintenance  # local import to avoid circular

    in_maint = await is_host_in_maintenance(db, host_id)
    if in_maint:
        return []

    # Evaluate CorrelationRule rows (the table the CRUD API manages and
    # seed_correlation_rules populates). Previously this iterated AlertRule,
    # whose rule_types (failed_logins, brute_force, ...) never matched the
    # matcher registry keys (sequence/co_occurrence/cross_host), so the engine
    # was effectively dead code.
    rules_result = await db.execute(select(CorrelationRule).where(CorrelationRule.enabled.is_(True)))
    rules = rules_result.scalars().all()
    now = datetime.now(timezone.utc)
    max_window = max((r.window_minutes or 20 for r in rules), default=30)
    since = now - timedelta(minutes=max_window)

    # Load recent events for this host
    events_result = await db.execute(
        select(Event).where(Event.host_id == host_id, Event.timestamp >= since).order_by(Event.timestamp)
    )
    events = events_result.scalars().all()

    results: list[CorrelationResult] = []

    for rule in rules:
        # rule_type is encoded in the description ([co_occurrence] /
        # [cross_host] prefixes; default sequence) — the model has no
        # rule_type column. Decode it the same way the CRUD API does.
        rule_type = rule_type_from_description(rule.description)
        matcher = MATCHERS.get(rule_type)
        if matcher is None:
            # Rule types without a registered matcher are skipped
            # rather than logged as warnings.
            logger.debug("No matcher registered for correlation rule_type=%s", rule_type)
            continue

        # Matchers return list[Event] | None (backward-compatible API).
        matched_events = matcher.matches(list(events), rule)
        if not matched_events:
            continue

        # Wrap into a CorrelationMatch so evidence/scoring/incident-creation
        # receive the structured object they expect.
        matched = build_correlation_match(matched_events, rule)
        confidence = matcher.score(matched)

        # Create alert linked to this correlation
        alert = await create_alert(
            db,
            host_id,
            matched.description or rule.description or "Correlation matched",
            matched.description or rule.description or f"Correlation matched: {rule.name}",
            rule.severity,
            rule.id,
            confidence=confidence,
            source=source,
            cooldown_minutes=rule.window_minutes or 15,
        )

        # Build CorrelationResult
        result = CorrelationResult(
            rule_id=rule.id,
            host_id=host_id,
            event_ids=[str(e.id) for e in matched.events],
            confidence=confidence,
            alert_id=alert.id if alert else None,
        )
        db.add(result)

        # Attempt to create an Incident from this correlation, if evidence is sufficient
        try:
            host_obj = type("HostObj", (), {"id": host_id})()  # minimal host obj
            incident = await _create_incident_from_correlation(
                db, host_obj, rule, matched, list(matched.events), source=source
            )
            if incident:
                # Store incident ID on the result for later reference
                result.incident_id = incident.id
        except Exception as exc:
            # Incident creation is best-effort; correlation result stands on its own
            logger.warning(
                "Incident creation failed for correlation rule %s: %s",
                rule.name,
                exc,
            )

        results.append(result)

    return results


# Legacy compatibility: run_correlation_engine with host object (not just host_id)
async def run_correlation_engine_for_host(db: AsyncSession, host: object, source: str | None = "host_scan") -> list[CorrelationResult]:
    """Accept a Host model instance instead of a bare host_id UUID."""

    host_id = getattr(host, "id", None)
    if not host_id:
        return []
    return await run_correlation_engine(db, host_id, source=source)


async def run_cross_host_correlation(db: AsyncSession) -> list[CorrelationResult]:
    """Run correlation engine across all hosts to detect cross-host patterns.

    Executes run_correlation_engine for each active host in the system.
    """
    from app.models.host import Host
    from sqlalchemy import select

    hosts_result = await db.execute(select(Host).where(Host.status == "online"))
    hosts = hosts_result.scalars().all()
    results: list[CorrelationResult] = []
    for host in hosts:
        host_results = await run_correlation_engine(db, host.id)
        results.extend(host_results)
    return results


async def seed_correlation_rules(db: AsyncSession) -> None:
    """Seed default correlation rules if none exist."""
    from sqlalchemy import select, func
    from app.models.correlation import CorrelationRule
    result = await db.execute(select(func.count()).select_from(CorrelationRule))
    if result.scalar_one() > 0:
        return
    defaults = [
        {"name": "SSH Brute Force Sequence", "description": "Sequence of ssh_login_failure → ssh_login_success", "event_sequence": ["ssh_login_failure", "ssh_login_success"], "window_minutes": 5, "min_occurrences": {"ssh_login_failure": 5}, "severity": "high"},
        {"name": "Privilege Escalation Sequence", "description": "Sequence of ssh_login_failure → sudo_usage", "event_sequence": ["ssh_login_failure", "sudo_usage"], "window_minutes": 5, "min_occurrences": {"ssh_login_failure": 3}, "severity": "critical"},
        {"name": "Cross-Host Correlation", "description": "[cross_host] Same IP fails SSH on 2+ hosts", "event_sequence": ["ssh_login_failure"], "window_minutes": 30, "min_occurrences": {"hosts": 2}, "severity": "high"},
        {"name": "Service Failure Incident", "description": "Single service_failure event", "event_sequence": ["service_failure"], "window_minutes": 1, "min_occurrences": 1, "severity": "high"},
        {"name": "File Integrity Change", "description": "Single file_integrity event", "event_sequence": ["file_integrity"], "window_minutes": 15, "min_occurrences": 1, "severity": "high"},
    ]
    for rule_data in defaults:
        existing = (
            await db.execute(select(CorrelationRule).where(CorrelationRule.name == rule_data["name"]))
        ).scalar_one_or_none()
        if not existing:
            rule = CorrelationRule(
                name=rule_data["name"],
                description=rule_data["description"],
                event_sequence=rule_data["event_sequence"],
                window_minutes=rule_data["window_minutes"],
                min_occurrences=rule_data["min_occurrences"],
                severity=rule_data["severity"],
                confidence_base=0.75,
                enabled=True,
                is_system=False,
            )
            db.add(rule)
    await db.commit()