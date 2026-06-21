"""Extensible correlation rule framework."""

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
        ...

    @abstractmethod
    def score(self, events: list[Event], rule: CorrelationRule) -> float:
        ...


class SequenceMatcher(CorrelationRuleMatcher):
    """Ordered event sequence matching with minimum occurrence counts."""

    def matches(self, events: list[Event], rule: CorrelationRule) -> list[Event] | None:
        window = timedelta(minutes=rule.window_minutes or 20)
        now = datetime.now(timezone.utc)
        recent = sorted(
            [e for e in events if e.timestamp >= now - window],
            key=lambda x: x.timestamp,
        )

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

    def score(self, events: list[Event], rule: CorrelationRule) -> float:
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


class CoOccurrenceMatcher(CorrelationRuleMatcher):
    """Detect co-occurring event types within a window (order-independent)."""

    def matches(self, events: list[Event], rule: CorrelationRule) -> list[Event] | None:
        window = timedelta(minutes=rule.window_minutes or 30)
        now = datetime.now(timezone.utc)
        recent = [e for e in events if e.timestamp >= now - window]
        required = set(rule.event_sequence or [])
        if not required:
            return None
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


MATCHERS: dict[str, CorrelationRuleMatcher] = {
    "sequence": SequenceMatcher(),
    "co_occurrence": CoOccurrenceMatcher(),
}
