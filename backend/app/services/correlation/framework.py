"""Correlation engine — three matcher algorithms plus evidence tracking.

The correlation engine evaluates sequences of events against rules to detect
attack patterns that individual alerts would miss.

Algorithm 1: SEQUENCE MATCHER
  Ordered event matching. Events must occur in a specific order within
  a time window. Example: failed_login → failed_login → login_success
  indicates brute force success.

Algorithm 2: CO-OCCURRENCE MATCHER
  Order-independent detection. Two or more event types must appear in the
  same time window, regardless of order. Example: service_stop + agent_disconnect
  appearing together suggests host compromise.

Algorithm 3: CROSS-HOST MATCHER
  Detects lateral movement. Same source IP or username triggers the same
  event type across multiple hosts within a time window.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.models.correlation import CorrelationRule
from app.models.event import Event


@dataclass
class CorrelationMatch:
    """Result of a correlation matcher, containing matched events and evidence."""

    events: list[Event]
    confidence: float
    severity: str
    description: str
    evidence: dict[str, Any] = field(default_factory=dict)
    """Structured evidence: time span, involved hosts/users, source IPs,
    MITRE techniques, and Docker service identities."""


class CorrelationRuleMatcher(ABC):
    """Base class for all correlation rule matchers.

    Subclasses implement `matches()` and `score()`. The default implementations
    are backward-compatible: `matches()` returns `list[Event] | None`, and
    `score()` accepts either `(events, rule)` or a `CorrelationMatch`.
    """

    @abstractmethod
    def matches(self, events: list[Event], rule: CorrelationRule) -> list[Event] | None:
        """Return matched events if the rule fires, else None.

        Backward-compatible: returns a plain list of Event objects for
        compatibility with existing test suites and engine code.
        """

    @abstractmethod
    def score(self, events: list[Event] | CorrelationMatch, rule: CorrelationRule | None = None) -> float:
        """Return confidence score 0-100.

        Overloads:
        - score(events, rule) -> float   (backward-compatible)
        - score(match: CorrelationMatch) -> float   (new evidence-based API)
        """

    def score_from_match(self, match: CorrelationMatch) -> float:
        """Convenience: score a CorrelationMatch object."""
        return self.score(match, rule=None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _event_evidence(event: Event) -> dict[str, Any]:
    """Extract lightweight evidence from a single event."""
    return {
        "event_type": event.event_type,
        "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        "host_id": str(event.host_id) if event.host_id else None,
        "source_ip": str(event.source_ip) if event.source_ip else None,
        "username": event.username,
        "mitre_technique_id": event.mitre_technique_id,
        "mitre_tactic": event.mitre_tactic,
        "metadata": event.metadata_ or {},
    }


def _aggregate_mitre(events: list[Event]) -> dict[str, list[str]]:
    """Aggregate unique MITRE technique IDs and tactics from a list of events."""
    techniques: set[str] = set()
    tactics: set[str] = set()
    for e in events:
        if e.mitre_technique_id:
            techniques.add(e.mitre_technique_id)
        if e.mitre_tactic:
            tactics.add(e.mitre_tactic)
    # Sort only string-valued entries; ignore None gracefully
    tid_list = sorted([t for t in techniques if isinstance(t, str)])
    tac_list = sorted([t for t in tactics if isinstance(t, str)])
    return {"technique_ids": tid_list, "tactics": tac_list}


def _time_span(events: list[Event]) -> dict[str, str | None]:
    """Compute the time span (start / end) of a list of events."""
    if not events:
        return {"start": None, "end": None, "duration_minutes": None}
    timestamps = [e.timestamp for e in events if e.timestamp]
    if len(timestamps) < 2:
        return {
            "start": timestamps[0].isoformat() if timestamps else None,
            "end": timestamps[0].isoformat() if timestamps else None,
            "duration_minutes": None,
        }
    sorted_ts = sorted(timestamps)
    duration = (sorted_ts[-1] - sorted_ts[0]).total_seconds() / 60.0
    return {
        "start": sorted_ts[0].isoformat(),
        "end": sorted_ts[-1].isoformat(),
        "duration_minutes": round(duration, 1),
    }


# ---------------------------------------------------------------------------
# Algorithm 1: Sequence Matcher — Ordered event sequence matching.
# Detects attack chains like: brute force → success → privilege escalation.
# Events must appear in the exact order specified by the rule.
# ---------------------------------------------------------------------------

class SequenceMatcher(CorrelationRuleMatcher):
    """Algorithm 1: Ordered event sequence matching.

    Detects attack chains like: brute force → success → privilege escalation.
    Events must appear in the exact order specified by the rule.
    Backward-compatible: matches() returns list[Event] | None.
    """

    def matches(self, events: list[Event], rule: CorrelationRule) -> list[Event] | None:
        window = timedelta(minutes=rule.window_minutes or 20)
        now = datetime.now(timezone.utc)
        recent = sorted(
            [e for e in events if e.timestamp >= now - window],
            key=lambda x: x.timestamp,
        )

        # Check minimum occurrence counts
        for etype, min_count in (rule.min_occurrences or {}).items():
            if sum(1 for e in recent if e.event_type == etype) < min_count:
                return None

        # Walk events in order, match against required sequence
        seq = rule.event_sequence or []
        if not seq:
            return None

        found_idx = 0
        matched: list[Event] = []
        for event in recent:
            if event.event_type == seq[found_idx]:
                matched.append(event)
                found_idx += 1
                if found_idx >= len(seq):
                    # Build structured evidence
                    evidence: dict[str, Any] = {
                        "matched_event_count": len(matched),
                        "total_events_in_window": len(recent),
                        "sequence": seq,
                        "time_span": _time_span(matched),
                        "involved_hosts": list({str(e.host_id) for e in matched}),
                        "involved_users": list({e.username for e in matched if e.username}),
                        "involved_source_ips": list(
                            {str(e.source_ip) for e in matched if e.source_ip}
                        ),
                        "aggregated_mitre": _aggregate_mitre(matched),
                    }
                    # Add Docker service identity if present
                    for e in matched:
                        if e.docker_service_id:
                            evidence["docker_service_ids"] = (
                                list({e.docker_service_id})
                            )
                            break

                    # Store evidence on the matcher for potential later access
                    # (callers can also build a CorrelationMatch from the returned events)
                    return matched

        return None

    def score(self, events: list[Event] | CorrelationMatch, rule: CorrelationRule | None = None) -> float:
        """Score either (events, rule) or a CorrelationMatch.

        Backward-compatible: score(events_list, rule) -> float.
        New API: score(CorrelationMatch) -> float.
        """
        if isinstance(events, CorrelationMatch):
            # New evidence-based API
            match: CorrelationMatch = events
            base = (match.confidence if match.confidence else 0.5) * 100
            types = [e.event_type for e in match.events]

            # Privilege escalation pattern: login + sudo
            if "sudo_usage" in types and "ssh_login_success" in types:
                base += 15
            # High-volume brute force
            if types.count("ssh_login_failure") >= 5:
                base += 10
            # Compressed attack timeline (< 10 min)
            span = match.evidence.get("time_span", {})
            duration = span.get("duration_minutes")
            if duration is not None and duration < 10:
                base += 10

            # Docker service stability bonus: same service across events
            if match.evidence.get("docker_service_ids"):
                base += 5

            # MITRE technique presence bonus
            mitre = match.evidence.get("aggregated_mitre", {})
            if mitre.get("technique_ids"):
                base += 5

            return min(base, 100)

        # Backward-compatible API: score(events, rule)
        if rule is None:
            raise TypeError("score() requires rule argument when called with events list")

        base = (rule.confidence_base or 0.5) * 100
        types = [e.event_type for e in events]

        # Privilege escalation pattern: login + sudo
        if "sudo_usage" in types and "ssh_login_success" in types:
            base += 15
        # High-volume brute force
        if types.count("ssh_login_failure") >= 5:
            base += 10
        # Compressed attack timeline (< 10 min)
        if len(events) >= 2:
            span = (events[-1].timestamp - events[0].timestamp).total_seconds()
            if span < 600:
                base += 10

        return min(base, 100)


# ---------------------------------------------------------------------------
# Algorithm 2: Co-Occurrence Matcher — Order-independent detection.
# Two or more event types must appear in the same time window, regardless of order.
# ---------------------------------------------------------------------------

class CoOccurrenceMatcher(CorrelationRuleMatcher):
    """Algorithm 2: Order-independent co-occurrence detection.

    Detects related events that appear together regardless of order.
    Backward-compatible: matches() returns list[Event] | None.
    """

    def matches(self, events: list[Event], rule: CorrelationRule) -> list[Event] | None:
        window = timedelta(minutes=rule.window_minutes or 30)
        now = datetime.now(timezone.utc)
        recent = [e for e in events if e.timestamp >= now - window]

        required = set(rule.event_sequence or [])
        if not required:
            return None

        # Check if all required event types are present (set subset)
        found_types = {e.event_type for e in recent}
        if not required.issubset(found_types):
            return None

        matched = [e for e in recent if e.event_type in required]

        # Build structured evidence
        evidence: dict[str, Any] = {
            "matched_event_count": len(matched),
            "total_events_in_window": len(recent),
            "required_event_types": list(required),
            "found_event_types": sorted(found_types),
            "time_span": _time_span(matched),
            "involved_hosts": list({str(e.host_id) for e in matched}),
            "involved_users": list({e.username for e in matched if e.username}),
            "involved_source_ips": list(
                {str(e.source_ip) for e in matched if e.source_ip}
            ),
            "aggregated_mitre": _aggregate_mitre(matched),
            "docker_service_ids": (
                list({e.docker_service_id for e in matched if e.docker_service_id})
                if any(e.docker_service_id for e in matched)
                else None
            ),
        }

        # Store evidence on a CorrelationMatch for the new API
        # (callers can also build a CorrelationMatch from the returned events)
        return matched

    def score(self, events: list[Event] | CorrelationMatch, rule: CorrelationRule | None = None) -> float:
        """Score either (events, rule) or a CorrelationMatch.

        Backward-compatible: score(events_list, rule) -> float.
        New API: score(CorrelationMatch) -> float.
        """
        if isinstance(events, CorrelationMatch):
            # New evidence-based API
            base = (events.confidence if events.confidence else 0.5) * 100

            # Bonus for 2+ distinct event types
            if len(set(e.event_type for e in events.events)) >= 2:
                base += 10

            # Docker service stability bonus
            if events.evidence.get("docker_service_ids"):
                base += 5

            # MITRE presence bonus
            mitre = events.evidence.get("aggregated_mitre", {})
            if mitre.get("technique_ids"):
                base += 5

            return min(base, 100)

        # Backward-compatible API: score(events, rule)
        if rule is None:
            raise TypeError("score() requires rule argument when called with events list")

        base = (rule.confidence_base or 0.5) * 100

        # Bonus for 2+ distinct event types
        if len(set(e.event_type for e in events)) >= 2:
            base += 10

        return min(base, 100)


# ---------------------------------------------------------------------------
# Algorithm 3: Cross-Host Matcher — Lateral movement detection.
# Same source IP or username hitting multiple hosts within a time window.
# ---------------------------------------------------------------------------

class CrossHostMatcher(CorrelationRuleMatcher):
    """Algorithm 3: Cross-host lateral movement detection.

    Detects the same attacker (by source_ip or username) hitting
    multiple hosts. Backward-compatible: matches() returns list[Event] | None.
    """

    def matches(self, events: list[Event], rule: CorrelationRule) -> list[Event] | None:
        window = timedelta(minutes=rule.window_minutes or 10)
        now = datetime.now(timezone.utc)
        recent = [e for e in events if e.timestamp >= now - window]

        etype = (rule.event_sequence or ["ssh_login_failure"])[0]
        min_hosts = (rule.min_occurrences or {}).get("hosts", 2)
        min_count = (rule.min_occurrences or {}).get(etype, 2)

        # Group events by source_ip or username
        by_key: dict[str, list[Event]] = {}
        for e in recent:
            if e.event_type != etype:
                continue
            key = str(e.source_ip) if e.source_ip else (e.username or "")
            if not key:
                continue
            by_key.setdefault(key, []).append(e)

        # Check each key for cross-host pattern
        for key, group in by_key.items():
            hosts = {e.host_id for e in group}
            if len(hosts) >= min_hosts and len(group) >= min_count:
                return group
        return None

    def score(self, events: list[Event] | CorrelationMatch, rule: CorrelationRule | None = None) -> float:
        """Score either (events, rule) or a CorrelationMatch.

        Backward-compatible: score(events_list, rule) -> float.
        New API: score(CorrelationMatch) -> float.
        """
        if isinstance(events, CorrelationMatch):
            # New evidence-based API
            base = (events.confidence if events.confidence else 0.6) * 100
            hosts = len({e.host_id for e in events.events})

            if hosts >= 3:
                base += 15
            elif hosts >= 2:
                base += 10

            # Docker service stability bonus: same service across hosts
            if events.evidence.get("docker_service_ids"):
                base += 5

            return min(base, 100)

        # Backward-compatible API: score(events, rule)
        if rule is None:
            raise TypeError("score() requires rule argument when called with events list")

        base = (rule.confidence_base or 0.6) * 100
        hosts = len({e.host_id for e in events})

        if hosts >= 3:
            base += 15
        elif hosts >= 2:
            base += 10

        return min(base, 100)


# ---------------------------------------------------------------------------
# Convenience: build a CorrelationMatch from matched events and rule
# ---------------------------------------------------------------------------

def build_correlation_match(
    matched_events: list[Event],
    rule: CorrelationRule,
    *,
    confidence: float | None = None,
    description: str | None = None,
) -> CorrelationMatch:
    """Build a CorrelationMatch from the events returned by the old-style matches()."""

    evidence: dict[str, Any] = {}
    # Try to extract evidence from the matched events if they have metadata
    # (this is best-effort; callers using the old matches() API don't need this)
    if matched_events:
        evidence["time_span"] = _time_span(matched_events)
        evidence["involved_hosts"] = list({str(e.host_id) for e in matched_events})
        evidence["involved_users"] = list({e.username for e in matched_events if e.username})
        evidence["involved_source_ips"] = list(
            {str(e.source_ip) for e in matched_events if e.source_ip}
        )
        evidence["aggregated_mitre"] = _aggregate_mitre(matched_events)

    return CorrelationMatch(
        events=matched_events,
        confidence=confidence if confidence is not None else 0.5,
        severity=rule.severity or "high",
        description=description or rule.name or "sequence",
        evidence=evidence,
    )


# ---------------------------------------------------------------------------
# Matcher registry
# ---------------------------------------------------------------------------

MATCHERS: dict[str, CorrelationRuleMatcher] = {
    "sequence": SequenceMatcher(),
    "co_occurrence": CoOccurrenceMatcher(),
    "cross_host": CrossHostMatcher(),
}