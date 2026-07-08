"""Correlation rule validation and preview helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.correlation import CorrelationRule
from app.models.event import Event
from app.models.host import Host
from app.services.correlation.framework import MATCHERS

VALID_RULE_TYPES = frozenset({"sequence", "co_occurrence", "cross_host"})
VALID_SEVERITIES = frozenset({"low", "medium", "high", "critical"})

SUPPORTED_EVENT_TYPES = [
    "ssh_login_failure",
    "ssh_login_success",
    "sudo_usage",
    "root_login",
    "brute_force",
    "service_failure",
    "service_start",
    "service_stop",
    "agent_disconnect",
    "agent_offline",
    "high_cpu",
    "high_memory",
    "high_disk",
    "network_flow",
    "network_connection",
]

RULE_TYPE_HELP: dict[str, dict[str, str]] = {
    "sequence": {
        "label": "Sequence",
        "summary": "Ordered event types within a time window (e.g. failed logins → success).",
    },
    "co_occurrence": {
        "label": "Co-occurrence",
        "summary": "Two or more event types in the same window (order does not matter).",
    },
    "cross_host": {
        "label": "Cross-host",
        "summary": "Same source IP or username failing across multiple hosts.",
    },
}

RULE_TEMPLATES: list[dict[str, Any]] = [
    {
        "name": "Brute Force Success",
        "rule_type": "sequence",
        "description": "Multiple failed logins followed by successful login",
        "event_sequence": ["ssh_login_failure", "ssh_login_success"],
        "window_minutes": 15,
        "min_occurrences": {"ssh_login_failure": 3},
        "severity": "critical",
        "confidence_base": 0.8,
    },
    {
        "name": "Privilege Escalation Suspicion",
        "rule_type": "sequence",
        "description": "Failed login followed by sudo usage",
        "event_sequence": ["ssh_login_failure", "sudo_usage"],
        "window_minutes": 20,
        "min_occurrences": {"ssh_login_failure": 2},
        "severity": "high",
        "confidence_base": 0.7,
    },
    {
        "name": "Service + Agent Disconnect",
        "rule_type": "co_occurrence",
        "description": "Service stop with agent disconnect",
        "event_sequence": ["service_stop", "agent_disconnect"],
        "window_minutes": 30,
        "min_occurrences": {},
        "severity": "critical",
        "confidence_base": 0.78,
    },
    {
        "name": "Cross-Host SSH Brute Force",
        "rule_type": "cross_host",
        "description": "Same IP fails SSH on 2+ hosts",
        "event_sequence": ["ssh_login_failure"],
        "window_minutes": 10,
        "min_occurrences": {"ssh_login_failure": 2, "hosts": 2},
        "severity": "high",
        "confidence_base": 0.72,
    },
]


@dataclass
class RuleDraft:
    rule_type: str
    event_sequence: list[str]
    window_minutes: int = 20
    min_occurrences: dict[str, int] | None = None
    severity: str = "high"
    confidence_base: float = 0.75
    name: str | None = None
    description: str | None = None


def description_for_type(description: str | None, rule_type: str) -> str | None:
    text = (description or "").strip()
    for prefix in ("[cross_host]", "[co_occurrence]"):
        if text.lower().startswith(prefix):
            text = text[len(prefix) :].strip()
    if rule_type == "co_occurrence":
        return f"[co_occurrence] {text}".strip() if text else "[co_occurrence]"
    if rule_type == "cross_host":
        return f"[cross_host] {text}".strip() if text else "[cross_host]"
    return text or None


def rule_type_from_description(description: str | None) -> str:
    desc = description or ""
    if desc.startswith("[cross_host]"):
        return "cross_host"
    if desc.startswith("[co_occurrence]"):
        return "co_occurrence"
    return "sequence"


def validate_rule_draft(draft: RuleDraft) -> list[str]:
    errors: list[str] = []
    if draft.rule_type not in VALID_RULE_TYPES:
        errors.append(f"rule_type must be one of {sorted(VALID_RULE_TYPES)}")
    if draft.severity not in VALID_SEVERITIES:
        errors.append(f"severity must be one of {sorted(VALID_SEVERITIES)}")
    if draft.window_minutes < 1 or draft.window_minutes > 1440:
        errors.append("window_minutes must be between 1 and 1440")
    if not draft.event_sequence:
        errors.append("event_sequence must include at least one event type")
    elif not all(isinstance(item, str) and item.strip() for item in draft.event_sequence):
        errors.append("event_sequence entries must be non-empty strings")
    elif draft.rule_type == "co_occurrence" and len(draft.event_sequence) < 2:
        errors.append("co_occurrence rules require at least 2 event types")
    if draft.confidence_base < 0 or draft.confidence_base > 1:
        errors.append("confidence_base must be between 0 and 1")
    for key, value in (draft.min_occurrences or {}).items():
        if not isinstance(value, int) or value < 1:
            errors.append(f"min_occurrences.{key} must be a positive integer")
    return errors


def draft_to_rule(draft: RuleDraft) -> CorrelationRule:
    return CorrelationRule(
        name=draft.name or "__preview__",
        description=description_for_type(draft.description, draft.rule_type),
        event_sequence=draft.event_sequence,
        window_minutes=draft.window_minutes,
        min_occurrences=draft.min_occurrences or {},
        severity=draft.severity,
        confidence_base=draft.confidence_base,
        enabled=True,
        is_system=False,
    )


async def preview_rule(
    db: AsyncSession,
    draft: RuleDraft,
    *,
    host_id: UUID | None = None,
    max_hosts: int = 25,
) -> dict[str, Any]:
    errors = validate_rule_draft(draft)
    if errors:
        return {"valid": False, "errors": errors, "matched": False}

    rule = draft_to_rule(draft)
    matcher = MATCHERS[draft.rule_type]
    window = rule.window_minutes or 20
    since = datetime.now(timezone.utc) - timedelta(minutes=window)

    if draft.rule_type == "cross_host":
        events = list(
            (
                await db.execute(select(Event).where(Event.timestamp >= since).order_by(Event.timestamp))
            ).scalars().all()
        )
        matched = matcher.matches(events, rule)
        host_ids = list({str(e.host_id) for e in matched}) if matched else []
        return {
            "valid": True,
            "matched": matched is not None,
            "rule_type": draft.rule_type,
            "event_count": len(matched) if matched else 0,
            "confidence": matcher.score(matched, rule) if matched else 0,
            "host_ids": host_ids,
            "matches": [{"host_id": hid, "event_count": len(matched or [])} for hid in host_ids],
        }

    host_query = select(Host.id, Host.name)
    if host_id:
        host_query = host_query.where(Host.id == host_id)
    else:
        host_query = host_query.limit(max_hosts)

    hosts = (await db.execute(host_query)).all()
    matches: list[dict[str, Any]] = []

    for hid, hname in hosts:
        events = list(
            (
                await db.execute(
                    select(Event)
                    .where(Event.host_id == hid, Event.timestamp >= since)
                    .order_by(Event.timestamp)
                )
            ).scalars().all()
        )
        matched = matcher.matches(events, rule)
        if matched:
            matches.append(
                {
                    "host_id": str(hid),
                    "host_name": hname,
                    "event_count": len(matched),
                    "confidence": round(matcher.score(matched, rule), 1),
                    "event_types": [e.event_type for e in matched],
                }
            )

    return {
        "valid": True,
        "matched": len(matches) > 0,
        "rule_type": draft.rule_type,
        "hosts_scanned": len(hosts),
        "matches": matches[:10],
    }


async def correlation_meta(db: AsyncSession) -> dict[str, Any]:
    event_types = (
        await db.execute(
            select(Event.event_type, func.count())
            .group_by(Event.event_type)
            .order_by(func.count().desc())
            .limit(50)
        )
    ).all()
    observed = [row[0] for row in event_types if row[0]]
    merged = list(dict.fromkeys(observed + SUPPORTED_EVENT_TYPES))

    return {
        "rule_types": [
            {"id": key, **RULE_TYPE_HELP[key]} for key in ("sequence", "co_occurrence", "cross_host")
        ],
        "event_types": merged,
        "severities": sorted(VALID_SEVERITIES),
        "templates": RULE_TEMPLATES,
        "fields": {
            "event_sequence": "Ordered steps for sequence rules; required set for co-occurrence",
            "min_occurrences": "Minimum counts per event type; cross_host supports hosts:N",
            "window_minutes": "Lookback window in minutes (1–1440)",
            "confidence_base": "Base confidence score multiplier (0.0–1.0)",
        },
    }
