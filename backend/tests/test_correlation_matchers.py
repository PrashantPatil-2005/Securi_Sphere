"""Tests for correlation matcher algorithms.

Tests the three matcher types (Sequence, Co-Occurrence, Cross-Host)
in isolation, without database queries. Uses mock Event objects.

IMPORTANT: The actual API uses:
- rule.event_sequence for sequence and co-occurrence types
- rule.confidence_base (not confidence) for scoring
- rule.min_occurrences dict with "hosts" key for cross-host
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.services.correlation.framework import (
    CoOccurrenceMatcher,
    CrossHostMatcher,
    SequenceMatcher,
)


def _make_event(event_type: str, ts: datetime, host_id=None, source_ip=None, username=None):
    """Create a mock Event with the fields the matchers read."""
    ev = MagicMock()
    ev.event_type = event_type
    ev.timestamp = ts
    ev.host_id = host_id or uuid4()
    ev.source_ip = source_ip
    ev.username = username
    ev.severity = "high"
    return ev


def _make_rule(event_sequence=None, min_occurrences=None, window_minutes=20,
               confidence_base=0.6, severity="high"):
    """Create a mock CorrelationRule matching the actual CorrelationRule schema."""
    rule = MagicMock()
    rule.event_sequence = event_sequence or []
    rule.min_occurrences = min_occurrences or {}
    rule.window_minutes = window_minutes
    rule.confidence_base = confidence_base
    rule.severity = severity
    rule.name = "test_rule"
    rule.description = "Test correlation rule"
    return rule


# ---------------------------------------------------------------------------
# Sequence Matcher
# ---------------------------------------------------------------------------

class TestSequenceMatcher:
    def test_exact_sequence_matches(self):
        matcher = SequenceMatcher()
        now = datetime.now(timezone.utc)
        events = [
            _make_event("ssh_login_failure", now - timedelta(minutes=5)),
            _make_event("ssh_login_failure", now - timedelta(minutes=4)),
            _make_event("ssh_login_success", now - timedelta(minutes=3)),
        ]
        rule = _make_rule(
            event_sequence=["ssh_login_failure", "ssh_login_success"],
            min_occurrences={"ssh_login_failure": 2},
        )
        result = matcher.matches(events, rule)
        assert result is not None
        # Sequence walker matches seq elements in order: 1 failure + 1 success = 2
        # (min_occurrences is a pre-filter check, not added to result)
        assert len(result) == 2
        assert result[0].event_type == "ssh_login_failure"
        assert result[1].event_type == "ssh_login_success"

    def test_wrong_order_no_match(self):
        matcher = SequenceMatcher()
        now = datetime.now(timezone.utc)
        events = [
            _make_event("ssh_login_success", now - timedelta(minutes=5)),
            _make_event("ssh_login_failure", now - timedelta(minutes=4)),
        ]
        rule = _make_rule(
            event_sequence=["ssh_login_failure", "ssh_login_success"],
        )
        result = matcher.matches(events, rule)
        assert result is None

    def test_missing_event_type_no_match(self):
        matcher = SequenceMatcher()
        now = datetime.now(timezone.utc)
        events = [
            _make_event("ssh_login_failure", now - timedelta(minutes=5)),
        ]
        rule = _make_rule(
            event_sequence=["ssh_login_failure", "ssh_login_success"],
        )
        result = matcher.matches(events, rule)
        assert result is None

    def test_outside_window_no_match(self):
        matcher = SequenceMatcher()
        now = datetime.now(timezone.utc)
        events = [
            _make_event("ssh_login_failure", now - timedelta(hours=2)),
            _make_event("ssh_login_success", now - timedelta(hours=1)),
        ]
        rule = _make_rule(
            event_sequence=["ssh_login_failure", "ssh_login_success"],
            window_minutes=30,
        )
        result = matcher.matches(events, rule)
        assert result is None

    def test_min_occurrences_not_met(self):
        matcher = SequenceMatcher()
        now = datetime.now(timezone.utc)
        events = [
            _make_event("ssh_login_failure", now - timedelta(minutes=5)),
            _make_event("ssh_login_success", now - timedelta(minutes=3)),
        ]
        rule = _make_rule(
            event_sequence=["ssh_login_failure", "ssh_login_success"],
            min_occurrences={"ssh_login_failure": 3},
        )
        result = matcher.matches(events, rule)
        assert result is None

    def test_empty_events_no_match(self):
        matcher = SequenceMatcher()
        rule = _make_rule(event_sequence=["ssh_login_failure", "ssh_login_success"])
        result = matcher.matches([], rule)
        assert result is None

    def test_returns_only_matched_events(self):
        """Sequence matcher returns only the matched subsequence, not all events."""
        matcher = SequenceMatcher()
        now = datetime.now(timezone.utc)
        events = [
            _make_event("ssh_login_failure", now - timedelta(minutes=10)),
            _make_event("ssh_login_failure", now - timedelta(minutes=5)),
            _make_event("ssh_login_failure", now - timedelta(minutes=4)),
            _make_event("ssh_login_success", now - timedelta(minutes=3)),
            _make_event("sudo_usage", now - timedelta(minutes=2)),
        ]
        rule = _make_rule(
            event_sequence=["ssh_login_failure", "ssh_login_success"],
            min_occurrences={"ssh_login_failure": 2},
        )
        result = matcher.matches(events, rule)
        assert result is not None
        # Sequence walker matches: first failure + first success = 2
        # (the extra failures and sudo_usage are not part of the sequence pattern)
        assert len(result) == 2
        assert result[0].event_type == "ssh_login_failure"
        assert result[1].event_type == "ssh_login_success"


# ---------------------------------------------------------------------------
# Co-Occurrence Matcher
# ---------------------------------------------------------------------------

class TestCoOccurrenceMatcher:
    def test_all_required_types_present(self):
        matcher = CoOccurrenceMatcher()
        now = datetime.now(timezone.utc)
        events = [
            _make_event("service_stop", now - timedelta(minutes=5)),
            _make_event("agent_disconnect", now - timedelta(minutes=3)),
        ]
        # Co-Occurrence uses event_sequence for required types
        rule = _make_rule(event_sequence=["service_stop", "agent_disconnect"])
        result = matcher.matches(events, rule)
        assert result is not None
        assert len(result) == 2

    def test_order_independent(self):
        matcher = CoOccurrenceMatcher()
        now = datetime.now(timezone.utc)
        events = [
            _make_event("agent_disconnect", now - timedelta(minutes=3)),
            _make_event("service_stop", now - timedelta(minutes=5)),
        ]
        rule = _make_rule(event_sequence=["service_stop", "agent_disconnect"])
        result = matcher.matches(events, rule)
        assert result is not None

    def test_missing_type_no_match(self):
        matcher = CoOccurrenceMatcher()
        now = datetime.now(timezone.utc)
        events = [
            _make_event("service_stop", now - timedelta(minutes=5)),
        ]
        rule = _make_rule(event_sequence=["service_stop", "agent_disconnect"])
        result = matcher.matches(events, rule)
        assert result is None

    def test_outside_window_no_match(self):
        matcher = CoOccurrenceMatcher()
        now = datetime.now(timezone.utc)
        events = [
            _make_event("service_stop", now - timedelta(hours=2)),
            _make_event("agent_disconnect", now - timedelta(minutes=3)),
        ]
        rule = _make_rule(
            event_sequence=["service_stop", "agent_disconnect"],
            window_minutes=30,
        )
        result = matcher.matches(events, rule)
        assert result is None

    def test_empty_required_returns_none(self):
        matcher = CoOccurrenceMatcher()
        now = datetime.now(timezone.utc)
        events = [_make_event("service_stop", now)]
        rule = _make_rule(event_sequence=[])
        result = matcher.matches(events, rule)
        assert result is None


# ---------------------------------------------------------------------------
# Cross-Host Matcher
# ---------------------------------------------------------------------------

class TestCrossHostMatcher:
    def test_same_ip_across_hosts(self):
        matcher = CrossHostMatcher()
        now = datetime.now(timezone.utc)
        host1, host2, host3 = uuid4(), uuid4(), uuid4()
        events = [
            _make_event("ssh_login_failure", now - timedelta(minutes=5), host_id=host1, source_ip="10.0.0.1"),
            _make_event("ssh_login_failure", now - timedelta(minutes=4), host_id=host2, source_ip="10.0.0.1"),
            _make_event("ssh_login_failure", now - timedelta(minutes=3), host_id=host3, source_ip="10.0.0.1"),
        ]
        rule = _make_rule(
            event_sequence=["ssh_login_failure"],
            min_occurrences={"hosts": 2, "ssh_login_failure": 3},
        )
        result = matcher.matches(events, rule)
        assert result is not None

    def test_different_ips_no_match(self):
        matcher = CrossHostMatcher()
        now = datetime.now(timezone.utc)
        host1, host2 = uuid4(), uuid4()
        events = [
            _make_event("ssh_login_failure", now - timedelta(minutes=5), host_id=host1, source_ip="10.0.0.1"),
            _make_event("ssh_login_failure", now - timedelta(minutes=4), host_id=host2, source_ip="10.0.0.2"),
        ]
        rule = _make_rule(
            event_sequence=["ssh_login_failure"],
            min_occurrences={"hosts": 2, "ssh_login_failure": 2},
        )
        result = matcher.matches(events, rule)
        assert result is None

    def test_single_host_no_match(self):
        matcher = CrossHostMatcher()
        now = datetime.now(timezone.utc)
        host1 = uuid4()
        events = [
            _make_event("ssh_login_failure", now - timedelta(minutes=5), host_id=host1, source_ip="10.0.0.1"),
            _make_event("ssh_login_failure", now - timedelta(minutes=4), host_id=host1, source_ip="10.0.0.1"),
        ]
        rule = _make_rule(
            event_sequence=["ssh_login_failure"],
            min_occurrences={"hosts": 2, "ssh_login_failure": 2},
        )
        result = matcher.matches(events, rule)
        assert result is None

    def test_username_grouping(self):
        matcher = CrossHostMatcher()
        now = datetime.now(timezone.utc)
        host1, host2 = uuid4(), uuid4()
        events = [
            _make_event("ssh_login_failure", now - timedelta(minutes=5), host_id=host1, username="admin"),
            _make_event("ssh_login_failure", now - timedelta(minutes=4), host_id=host2, username="admin"),
        ]
        rule = _make_rule(
            event_sequence=["ssh_login_failure"],
            min_occurrences={"hosts": 2, "ssh_login_failure": 2},
        )
        result = matcher.matches(events, rule)
        assert result is not None

    def test_outside_window_no_match(self):
        matcher = CrossHostMatcher()
        now = datetime.now(timezone.utc)
        host1, host2 = uuid4(), uuid4()
        events = [
            _make_event("ssh_login_failure", now - timedelta(hours=2), host_id=host1, source_ip="10.0.0.1"),
            _make_event("ssh_login_failure", now - timedelta(minutes=4), host_id=host2, source_ip="10.0.0.1"),
        ]
        rule = _make_rule(
            event_sequence=["ssh_login_failure"],
            min_occurrences={"hosts": 2, "ssh_login_failure": 2},
            window_minutes=30,
        )
        result = matcher.matches(events, rule)
        assert result is None

    def test_no_source_ip_or_username_skips_event(self):
        """Events with neither source_ip nor username are skipped."""
        matcher = CrossHostMatcher()
        now = datetime.now(timezone.utc)
        host1, host2 = uuid4(), uuid4()
        events = [
            _make_event("ssh_login_failure", now - timedelta(minutes=5), host_id=host1),
            _make_event("ssh_login_failure", now - timedelta(minutes=4), host_id=host2),
        ]
        rule = _make_rule(
            event_sequence=["ssh_login_failure"],
            min_occurrences={"hosts": 2, "ssh_login_failure": 2},
        )
        result = matcher.matches(events, rule)
        assert result is None


# ---------------------------------------------------------------------------
# Confidence Scoring
# ---------------------------------------------------------------------------

class TestConfidenceScoring:
    def test_sequence_score_above_base(self):
        matcher = SequenceMatcher()
        now = datetime.now(timezone.utc)
        events = [
            _make_event("ssh_login_failure", now - timedelta(minutes=1)),
            _make_event("ssh_login_failure", now - timedelta(minutes=1)),
            _make_event("ssh_login_failure", now - timedelta(minutes=1)),
            _make_event("ssh_login_failure", now - timedelta(minutes=1)),
            _make_event("ssh_login_failure", now - timedelta(minutes=1)),
            _make_event("ssh_login_success", now),
            _make_event("sudo_usage", now),
        ]
        rule = _make_rule(confidence_base=0.5)
        score = matcher.score(events, rule)
        # Should get bonuses for high-volume + compressed timeline + sudo
        assert score > 50

    def test_co_occurrence_score_above_base(self):
        matcher = CoOccurrenceMatcher()
        now = datetime.now(timezone.utc)
        events = [
            _make_event("service_stop", now - timedelta(minutes=5)),
            _make_event("agent_disconnect", now - timedelta(minutes=3)),
        ]
        rule = _make_rule(confidence_base=0.4)
        score = matcher.score(events, rule)
        assert score > 40

    def test_cross_host_score_scales_with_hosts(self):
        matcher = CrossHostMatcher()
        now = datetime.now(timezone.utc)
        hosts = [uuid4() for _ in range(5)]
        events = [
            _make_event("ssh_login_failure", now - timedelta(minutes=i), host_id=h, source_ip="10.0.0.1")
            for i, h in enumerate(hosts)
        ]
        rule = _make_rule(confidence_base=0.4)
        score = matcher.score(events, rule)
        # 5 hosts should give a significant bonus
        assert score > 50

    def test_score_never_exceeds_100(self):
        matcher = SequenceMatcher()
        now = datetime.now(timezone.utc)
        events = [_make_event("ssh_login_failure", now - timedelta(minutes=i)) for i in range(100)]
        events.append(_make_event("ssh_login_success", now))
        events.append(_make_event("sudo_usage", now))
        rule = _make_rule(confidence_base=0.9)
        score = matcher.score(events, rule)
        assert score <= 100

    def test_score_no_bonus_without_patterns(self):
        """Score stays near base when no high-volume/sudo patterns are present.
        Gets +10 for compressed timeline (< 10 min span) regardless."""
        matcher = SequenceMatcher()
        now = datetime.now(timezone.utc)
        events = [
            _make_event("ssh_login_failure", now - timedelta(minutes=30)),
            _make_event("ssh_login_failure", now - timedelta(minutes=15)),
        ]
        rule = _make_rule(confidence_base=0.5)
        score = matcher.score(events, rule)
        # No sudo, no high-volume (< 5 failures), span > 10 min -> just base 50
        assert score == 50.0

    def test_cross_host_single_host_base_score(self):
        """Single host gives base score only."""
        matcher = CrossHostMatcher()
        now = datetime.now(timezone.utc)
        host1 = uuid4()
        events = [
            _make_event("ssh_login_failure", now - timedelta(minutes=i), host_id=host1, source_ip="10.0.0.1")
            for i in range(5)
        ]
        rule = _make_rule(confidence_base=0.6)
        score = matcher.score(events, rule)
        assert score == 60.0
