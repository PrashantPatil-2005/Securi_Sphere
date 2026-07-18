"""Correlation engine — three matcher algorithms.

The correlation engine evaluates sequences of events against rules to detect
attack patterns that individual alerts would miss.

Algorithm 1: SEQUENCE MATCHER
  Ordered event matching. Events must occur in a specific order within
  a time window. Example: failed_login → failed_login → login_success
  indicates brute force success.

  Algorithm:
  1. Filter events to the rule's time window
  2. Check minimum occurrence counts per event type
  3. Walk events in timestamp order, matching against the required sequence
  4. Return matched events if full sequence found

  Confidence scoring:
  - Base score from rule definition (0.0-1.0)
  - +15% if sudo_usage + ssh_login_success (privilege escalation pattern)
  - +10% if 5+ failed logins (high-volume brute force)
  - +10% if events span < 10 minutes (compressed attack timeline)

Algorithm 2: CO-OCCURRENCE MATCHER
  Order-independent detection. Two or more event types must appear in the
  same time window, regardless of order. Example: service_stop + agent_disconnect
  appearing together suggests host compromise.

  Algorithm:
  1. Filter events to the rule's time window
  2. Collect unique event types present
  3. Check if all required types are present (set subset check)
  4. Return all matching events

  Confidence scoring:
  - Base score from rule definition
  - +10% if 2+ distinct event types present

Algorithm 3: CROSS-HOST MATCHER
  Detects lateral movement. Same source IP or username triggers the same
  event type across multiple hosts within a time window.

  Algorithm:
  1. Filter events to the rule's time window
  2. Group by source_ip or username (the "key")
  3. For each key, count distinct hosts and total events
  4. Match if hosts >= min_hosts AND events >= min_count

  Confidence scoring:
  - Base score from rule definition
  - +10% if 2 hosts affected
  - +15% if 3+ hosts affected (wider lateral movement)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.models.correlation import CorrelationRule
from app.models.event import Event


@dataclass
class CorrelationMatch:
    rule_name: str
    events: list[Event]
    confidence: float
    severity: str
    description: str


class CorrelationRuleMatcher(ABC):
    @abstractmethod
    def matches(self, events: list[Event], rule: CorrelationRule) -> list[Event] | None:
        """Return matched events if rule fires, else None."""
        ...

    @abstractmethod
    def score(self, events: list[Event], rule: CorrelationRule) -> float:
        """Return confidence score 0-100."""
        ...


class SequenceMatcher(CorrelationRuleMatcher):
    """Algorithm 1: Ordered event sequence matching.

    Detects attack chains like: brute force → success → privilege escalation.
    Events must appear in the exact order specified by the rule.
    """

    def matches(self, events: list[Event], rule: CorrelationRule) -> list[Event] | None:
        window = timedelta(minutes=rule.window_minutes or 20)
        now = datetime.now(timezone.utc)
        recent = sorted(
            [e for e in events if e.timestamp >= now - window],
            key=lambda x: x.timestamp,
        )

        # Step 1: Check minimum occurrence counts
        for etype, min_count in (rule.min_occurrences or {}).items():
            if sum(1 for e in recent if e.event_type == etype) < min_count:
                return None

        # Step 2: Walk events in order, match against required sequence
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

    def score(self, events: list[Event], rule: CorrelationRule) -> float:
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


class CoOccurrenceMatcher(CorrelationRuleMatcher):
    """Algorithm 2: Order-independent co-occurrence detection.

    Detects related events that appear together regardless of order.
    Example: service_stop + agent_disconnect = host compromise indicator.
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
        return matched if matched else None

    def score(self, events: list[Event], rule: CorrelationRule) -> float:
        base = (rule.confidence_base or 0.5) * 100
        if len(set(e.event_type for e in events)) >= 2:
            base += 10
        return min(base, 100)


class CrossHostMatcher(CorrelationRuleMatcher):
    """Algorithm 3: Cross-host lateral movement detection.

    Detects the same attacker (by source_ip or username) hitting
    multiple hosts. Example: same IP fails SSH on 3 hosts within
    10 minutes = credential stuffing / lateral movement.
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

    def score(self, events: list[Event], rule: CorrelationRule) -> float:
        base = (rule.confidence_base or 0.6) * 100
        hosts = len({e.host_id for e in events})
        if hosts >= 3:
            base += 15
        elif hosts >= 2:
            base += 10
        return min(base, 100)


MATCHERS: dict[str, CorrelationRuleMatcher] = {
    "sequence": SequenceMatcher(),
    "co_occurrence": CoOccurrenceMatcher(),
    "cross_host": CrossHostMatcher(),
}
