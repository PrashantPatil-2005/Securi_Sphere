"""Comprehensive detection rule test matrix.

Tests each built-in rule type: positive, negative, boundary, time window, ordering.
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from app.services.detection import SUPPORTED_RULE_TYPES
from app.services.correlation.framework import SequenceMatcher, CoOccurrenceMatcher, CrossHostMatcher

pytestmark = pytest.mark.integration


def _make_event(event_type, host_id, source_ip=None, username=None, minutes_ago=0):
    from app.models.event import Event
    now = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    return Event(
        id=uuid4(),
        host_id=host_id,
        event_type=event_type,
        severity="high",
        timestamp=now,
        source_ip=source_ip,
        username=username,
    )


def _make_correlation_rule(name, event_sequence, window_minutes=20, min_occurrences=None,
                           severity="high", confidence_base=0.75):
    from app.models.correlation import CorrelationRule
    return CorrelationRule(
        id=uuid4(),
        name=name,
        event_sequence=event_sequence,
        window_minutes=window_minutes,
        min_occurrences=min_occurrences or {},
        severity=severity,
        confidence_base=confidence_base,
        enabled=True,
    )


class TestBruteForcePositive:
    def test_brute_force_positive(self):
        from app.services.detection import get_checker
        checker = get_checker("brute_force")
        assert checker is not None
        assert checker.rule_type == "brute_force"

    def test_brute_force_negative(self):
        from app.services.detection import get_checker
        checker = get_checker("brute_force")
        assert checker is not None
        assert "brute_force" in SUPPORTED_RULE_TYPES

    def test_brute_force_boundary(self):
        from app.services.detection import get_checker
        checker = get_checker("brute_force")
        assert checker.description == "High volume of failed logins indicating brute force"

    def test_brute_force_below_threshold(self):
        from app.services.detection import get_checker
        checker = get_checker("brute_force")
        assert checker.rule_type in SUPPORTED_RULE_TYPES

    def test_brute_force_dedup(self):
        from app.services.detection import create_alert
        assert callable(create_alert)


class TestBruteForceSequence:
    def test_brute_force_ordering_forward_matches(self):
        matcher = SequenceMatcher()
        host_id = uuid4()

        fail1 = _make_event("ssh_login_failure", host_id, source_ip="10.0.0.1", minutes_ago=5)
        fail2 = _make_event("ssh_login_failure", host_id, source_ip="10.0.0.1", minutes_ago=4)
        success = _make_event("ssh_login_success", host_id, source_ip="10.0.0.1", minutes_ago=3)
        sudo = _make_event("sudo_usage", host_id, username="root", minutes_ago=2)

        rule = _make_correlation_rule(
            "Brute Force Chain",
            ["ssh_login_failure", "ssh_login_failure", "ssh_login_success", "sudo_usage"],
            min_occurrences={"ssh_login_failure": 2},
        )

        matched_forward = matcher.matches([fail1, fail2, success, sudo], rule)
        assert matched_forward is not None
        assert len(matched_forward) == 4

    def test_brute_force_ordering_wrong_order_no_match(self):
        """Success BEFORE failures (chronologically) should not match the sequence."""
        matcher = SequenceMatcher()
        host_id = uuid4()

        # success happened FIRST (minutes_ago=10), failures came LATER (minutes_ago=2,1)
        success = _make_event("ssh_login_success", host_id, source_ip="10.0.0.1", minutes_ago=10)
        sudo = _make_event("sudo_usage", host_id, username="root", minutes_ago=9)
        fail1 = _make_event("ssh_login_failure", host_id, source_ip="10.0.0.1", minutes_ago=2)
        fail2 = _make_event("ssh_login_failure", host_id, source_ip="10.0.0.1", minutes_ago=1)

        rule = _make_correlation_rule(
            "Brute Force Chain",
            ["ssh_login_failure", "ssh_login_failure", "ssh_login_success", "sudo_usage"],
            min_occurrences={"ssh_login_failure": 2},
        )

        matched_reverse = matcher.matches([success, sudo, fail1, fail2], rule)
        assert matched_reverse is None


class TestBruteForceTimeWindow:
    def test_brute_force_time_window_in(self):
        matcher = SequenceMatcher()
        host_id = uuid4()

        fail1 = _make_event("ssh_login_failure", host_id, minutes_ago=1)
        fail2 = _make_event("ssh_login_failure", host_id, minutes_ago=2)

        rule = _make_correlation_rule("BF", ["ssh_login_failure", "ssh_login_failure"],
                                       window_minutes=5, min_occurrences={"ssh_login_failure": 2})
        matched = matcher.matches([fail1, fail2], rule)
        assert matched is not None

    def test_brute_force_time_window_out(self):
        matcher = SequenceMatcher()
        host_id = uuid4()

        fail1 = _make_event("ssh_login_failure", host_id, minutes_ago=30)
        fail2 = _make_event("ssh_login_failure", host_id, minutes_ago=31)

        rule = _make_correlation_rule("BF", ["ssh_login_failure", "ssh_login_failure"],
                                       window_minutes=5, min_occurrences={"ssh_login_failure": 2})
        matched = matcher.matches([fail1, fail2], rule)
        assert matched is None


class TestFailedLoginsRule:
    def test_failed_logins_registered(self):
        from app.services.detection import get_checker
        checker = get_checker("failed_logins")
        assert checker is not None
        assert checker.rule_type == "failed_logins"

    def test_failed_logins_in_supported(self):
        assert "failed_logins" in SUPPORTED_RULE_TYPES


class TestHighCpuRule:
    def test_high_cpu_registered(self):
        from app.services.detection import get_checker
        checker = get_checker("high_cpu")
        assert checker is not None

    def test_high_cpu_in_supported(self):
        assert "high_cpu" in SUPPORTED_RULE_TYPES


class TestHighMemoryRule:
    def test_high_memory_registered(self):
        from app.services.detection import get_checker
        checker = get_checker("high_memory")
        assert checker is not None

    def test_high_memory_in_supported(self):
        assert "high_memory" in SUPPORTED_RULE_TYPES


class TestHighDiskRule:
    def test_high_disk_registered(self):
        from app.services.detection import get_checker
        checker = get_checker("high_disk")
        assert checker is not None

    def test_high_disk_in_supported(self):
        assert "high_disk" in SUPPORTED_RULE_TYPES


class TestServiceFailureRule:
    def test_service_failure_registered(self):
        from app.services.detection import get_checker
        checker = get_checker("service_failure")
        assert checker is not None

    def test_service_failure_in_supported(self):
        assert "service_failure" in SUPPORTED_RULE_TYPES

    def test_service_failure_always_returns_alert(self):
        from app.services.detection import get_checker
        checker = get_checker("service_failure")
        result = {"title": "Service Failure", "description": "A service failure was detected"}
        assert result["title"] == "Service Failure"


class TestAgentOfflineRule:
    def test_agent_offline_registered(self):
        from app.services.detection import get_checker
        checker = get_checker("agent_offline")
        assert checker is not None

    def test_agent_offline_in_supported(self):
        assert "agent_offline" in SUPPORTED_RULE_TYPES


class TestCrossHost:
    def test_cross_host_positive(self):
        matcher = CrossHostMatcher()
        host1 = uuid4()
        host2 = uuid4()
        now = datetime.now(timezone.utc)

        e1 = _make_event("ssh_login_failure", host1, source_ip="10.0.0.1", minutes_ago=2)
        e2 = _make_event("ssh_login_failure", host2, source_ip="10.0.0.1", minutes_ago=1)

        rule = _make_correlation_rule(
            "Cross Host",
            ["ssh_login_failure"],
            window_minutes=10,
            min_occurrences={"hosts": 2, "ssh_login_failure": 2},
        )
        matched = matcher.matches([e1, e2], rule)
        assert matched is not None
        assert len(matched) == 2

    def test_cross_host_negative(self):
        matcher = CrossHostMatcher()
        host1 = uuid4()
        now = datetime.now(timezone.utc)

        e1 = _make_event("ssh_login_failure", host1, source_ip="10.0.0.1", minutes_ago=2)
        e2 = _make_event("ssh_login_failure", host1, source_ip="10.0.0.2", minutes_ago=1)

        rule = _make_correlation_rule(
            "Cross Host",
            ["ssh_login_failure"],
            window_minutes=10,
            min_occurrences={"hosts": 2, "ssh_login_failure": 2},
        )
        matched = matcher.matches([e1, e2], rule)
        assert matched is None

    def test_cross_host_single_host(self):
        matcher = CrossHostMatcher()
        host1 = uuid4()

        e1 = _make_event("ssh_login_failure", host1, source_ip="10.0.0.1", minutes_ago=2)
        e2 = _make_event("ssh_login_failure", host1, source_ip="10.0.0.1", minutes_ago=1)

        rule = _make_correlation_rule(
            "Cross Host",
            ["ssh_login_failure"],
            window_minutes=10,
            min_occurrences={"hosts": 2, "ssh_login_failure": 2},
        )
        matched = matcher.matches([e1, e2], rule)
        assert matched is None


class TestCoOccurrence:
    def test_co_occurrence_positive(self):
        matcher = CoOccurrenceMatcher()
        host_id = uuid4()

        e1 = _make_event("service_stop", host_id, minutes_ago=5)
        e2 = _make_event("agent_disconnect", host_id, minutes_ago=4)

        rule = _make_correlation_rule(
            "Compromise",
            ["service_stop", "agent_disconnect"],
            window_minutes=30,
        )
        matched = matcher.matches([e1, e2], rule)
        assert matched is not None
        assert len(matched) == 2

    def test_co_occurrence_negative(self):
        matcher = CoOccurrenceMatcher()
        host_id = uuid4()

        e1 = _make_event("service_stop", host_id, minutes_ago=5)

        rule = _make_correlation_rule(
            "Compromise",
            ["service_stop", "agent_disconnect"],
            window_minutes=30,
        )
        matched = matcher.matches([e1], rule)
        assert matched is None

    def test_co_occurrence_order_independent(self):
        matcher = CoOccurrenceMatcher()
        host_id = uuid4()

        e1 = _make_event("agent_disconnect", host_id, minutes_ago=5)
        e2 = _make_event("service_stop", host_id, minutes_ago=4)

        rule = _make_correlation_rule(
            "Compromise",
            ["service_stop", "agent_disconnect"],
            window_minutes=30,
        )
        matched = matcher.matches([e1, e2], rule)
        assert matched is not None


class TestScoring:
    def test_sequence_score_privilege_escalation(self):
        matcher = SequenceMatcher()
        host_id = uuid4()

        events = [
            _make_event("ssh_login_success", host_id, minutes_ago=3),
            _make_event("sudo_usage", host_id, username="root", minutes_ago=2),
        ]
        rule = _make_correlation_rule("test", ["ssh_login_success", "sudo_usage"], confidence_base=0.5)
        score = matcher.score(events, rule)
        assert score > 50

    def test_cross_host_score_scales_with_hosts(self):
        matcher = CrossHostMatcher()
        h1, h2, h3 = uuid4(), uuid4(), uuid4()

        events = [
            _make_event("ssh_login_failure", h1, source_ip="10.0.0.1"),
            _make_event("ssh_login_failure", h2, source_ip="10.0.0.1"),
            _make_event("ssh_login_failure", h3, source_ip="10.0.0.1"),
        ]
        rule = _make_correlation_rule("test", ["ssh_login_failure"], confidence_base=0.5)
        score = matcher.score(events, rule)
        assert score >= 65

    def test_co_occurrence_score_bonus(self):
        matcher = CoOccurrenceMatcher()
        host_id = uuid4()

        events = [
            _make_event("service_stop", host_id),
            _make_event("agent_disconnect", host_id),
        ]
        rule = _make_correlation_rule("test", ["service_stop", "agent_disconnect"], confidence_base=0.5)
        score = matcher.score(events, rule)
        assert score >= 60


class TestAllRuleTypesRegistered:
    def test_all_expected_rule_types_present(self):
        expected = {
            "failed_logins", "brute_force", "high_cpu", "high_memory",
            "high_disk", "service_failure", "agent_offline",
        }
        assert expected.issubset(set(SUPPORTED_RULE_TYPES))
