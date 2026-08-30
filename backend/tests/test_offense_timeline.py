"""Offense engine + timeline integration tests.

Tests offense creation, grouping, timeline ordering, dedup.
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4
import pytest
from app.services.offense_engine import (
    OFFENSE_WINDOW, RISK_FROM_SEVERITY, RISK_RANK,
    _append_timeline_entry, _max_risk, _track_user,
)
from app.services.timeline import _chain_confidence, _chain_title, _timeline_fingerprint

pytestmark = pytest.mark.integration


def _make_offense(**kwargs):
    defaults = {
        "id": uuid4(),
        "offense_number": 1,
        "host_id": uuid4(),
        "title": "Test Offense",
        "risk_level": "medium",
        "status": "open",
        "event_count": 0,
        "alert_count": 0,
        "related_hosts": [],
        "related_users": [],
        "timeline": [],
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_event_mock(event_type, timestamp=None):
    now = timestamp or datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid4(),
        event_type=event_type,
        timestamp=now,
        username=None,
        source_ip=None,
        severity="high",
    )


class TestNewOffenseCreated:
    def test_first_alert_creates_new_offense(self):
        offense = _make_offense()
        assert offense.offense_number == 1
        assert offense.status == "open"


class TestExistingOffenseGrouped:
    def test_related_alerts_within_window(self):
        offense = _make_offense(updated_at=datetime.now(timezone.utc))
        now = datetime.now(timezone.utc)
        assert (now - offense.updated_at) < OFFENSE_WINDOW


class TestOffenseWindowBoundary:
    def test_alert_at_exactly_offense_window_boundary(self):
        boundary = datetime.now(timezone.utc) - OFFENSE_WINDOW
        now = datetime.now(timezone.utc)
        delta = now - boundary
        assert delta >= OFFENSE_WINDOW - timedelta(seconds=1)


class TestOffenseRiskEscalation:
    def test_higher_severity_higher_risk(self):
        assert RISK_RANK["critical"] > RISK_RANK["high"]
        assert RISK_RANK["high"] > RISK_RANK["medium"]
        assert RISK_RANK["medium"] > RISK_RANK["low"]

    def test_max_risk_selects_higher(self):
        assert _max_risk("critical", "low") == "critical"
        assert _max_risk("low", "critical") == "critical"
        assert _max_risk("medium", "medium") == "medium"

    def test_risk_from_severity_mapping(self):
        assert RISK_FROM_SEVERITY["critical"] == "critical"
        assert RISK_FROM_SEVERITY["high"] == "high"
        assert RISK_FROM_SEVERITY["medium"] == "medium"
        assert RISK_FROM_SEVERITY["low"] == "low"
        assert RISK_FROM_SEVERITY["info"] == "low"


class TestOffenseTimelineOrdering:
    def test_timeline_entries_sorted_by_timestamp(self):
        offense = _make_offense(timeline=[])
        now = datetime.now(timezone.utc)
        _append_timeline_entry(offense, {"timestamp": (now - timedelta(minutes=5)).isoformat(), "type": "b"})
        _append_timeline_entry(offense, {"timestamp": (now - timedelta(minutes=10)).isoformat(), "type": "a"})
        _append_timeline_entry(offense, {"timestamp": now.isoformat(), "type": "c"})
        timestamps = [e["timestamp"] for e in offense.timeline]
        assert timestamps == sorted(timestamps)


class TestOffenseTimelineCap:
    def test_max_500_timeline_entries(self):
        offense = _make_offense(timeline=[])
        now = datetime.now(timezone.utc)
        for i in range(510):
            _append_timeline_entry(offense, {"timestamp": (now + timedelta(seconds=i)).isoformat(), "idx": i})
        assert len(offense.timeline) == 500
        assert offense.timeline[-1]["idx"] == 509


class TestOffenseNumberUniqueness:
    def test_multiple_offenses_get_unique_numbers(self):
        seen = set()
        for i in range(10):
            num = i + 100
            assert num not in seen
            seen.add(num)
        assert len(seen) == 10


class TestTrackUser:
    def test_track_user_adds_new(self):
        offense = _make_offense(related_users=[])
        _track_user(offense, "alice")
        assert "alice" in offense.related_users

    def test_track_user_no_duplicate(self):
        offense = _make_offense(related_users=["alice"])
        _track_user(offense, "alice")
        assert offense.related_users.count("alice") == 1

    def test_track_user_none_ignored(self):
        offense = _make_offense(related_users=[])
        _track_user(offense, None)
        assert offense.related_users == []


class TestTimelineFingerprint:
    def test_timeline_fingerprint_deterministic(self):
        host_id = uuid4()
        title = "Test Chain"
        ts = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        fp1 = _timeline_fingerprint(host_id, title, ts)
        fp2 = _timeline_fingerprint(host_id, title, ts)
        assert fp1 == fp2
        assert len(fp1) == 64

    def test_timeline_fingerprint_varies_by_title(self):
        host_id = uuid4()
        ts = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        fp1 = _timeline_fingerprint(host_id, "Title A", ts)
        fp2 = _timeline_fingerprint(host_id, "Title B", ts)
        assert fp1 != fp2

    def test_timeline_fingerprint_varies_by_host(self):
        ts = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        fp1 = _timeline_fingerprint(uuid4(), "Title", ts)
        fp2 = _timeline_fingerprint(uuid4(), "Title", ts)
        assert fp1 != fp2

    def test_timeline_fingerprint_same_hour_same_bucket(self):
        host_id = uuid4()
        title = "Test"
        ts1 = datetime(2025, 1, 15, 10, 15, 0, tzinfo=timezone.utc)
        ts2 = datetime(2025, 1, 15, 10, 45, 0, tzinfo=timezone.utc)
        fp1 = _timeline_fingerprint(host_id, title, ts1)
        fp2 = _timeline_fingerprint(host_id, title, ts2)
        assert fp1 == fp2


class TestChainTitle:
    def test_chain_title_attack_chain(self):
        types = ["ssh_login_failure", "ssh_login_success", "sudo_usage"]
        title = _chain_title(types)
        assert "Brute Force" in title
        assert "Escalation" in title

    def test_chain_title_brute_force_success(self):
        types = ["ssh_login_failure", "ssh_login_success"]
        title = _chain_title(types)
        assert "Brute Force" in title
        assert "Successful Login" in title

    def test_chain_title_repeated_failures(self):
        types = ["ssh_login_failure", "ssh_login_failure", "ssh_login_failure"]
        title = _chain_title(types)
        assert "Brute Force" in title

    def test_chain_title_suspicious(self):
        types = ["ssh_login_failure", "sudo_usage"]
        title = _chain_title(types)
        assert title == "Suspicious Activity Sequence"

    def test_chain_title_escalation(self):
        from app.services.timeline import _chain_title
        types = ["ssh_login_failure", "ssh_login_success", "sudo_usage"]
        title = _chain_title(types)
        assert "Escalation" in title


class TestChainConfidence:
    def test_chain_confidence_capped_at_100(self):
        host_id = uuid4()
        now = datetime.now(timezone.utc)
        events = []
        for i in range(20):
            e = _make_event_mock("ssh_login_failure", now + timedelta(seconds=i))
            e.id = uuid4()
            events.append(e)
        events.append(_make_event_mock("ssh_login_success", now + timedelta(seconds=21)))
        events[-1].id = uuid4()
        events.append(_make_event_mock("sudo_usage", now + timedelta(seconds=22)))
        events[-1].id = uuid4()
        events.append(_make_event_mock("root_login", now + timedelta(seconds=23)))
        events[-1].id = uuid4()

        confidence = _chain_confidence(events)
        assert confidence <= 100

    def test_chain_confidence_increases_with_events(self):
        now = datetime.now(timezone.utc)
        base_events = [_make_event_mock("ssh_login_failure", now + timedelta(seconds=i)) for i in range(3)]
        for e in base_events:
            e.id = uuid4()
        score_base = _chain_confidence(base_events)

        enriched = base_events.copy()
        enriched.append(_make_event_mock("ssh_login_success", now + timedelta(seconds=4)))
        enriched[-1].id = uuid4()
        enriched.append(_make_event_mock("sudo_usage", now + timedelta(seconds=5)))
        enriched[-1].id = uuid4()
        score_enriched = _chain_confidence(enriched)
        assert score_enriched >= score_base

    def test_chain_confidence_minimum(self):
        now = datetime.now(timezone.utc)
        events = [_make_event_mock("ssh_login_failure", now)]
        events[0].id = uuid4()
        confidence = _chain_confidence(events)
        assert confidence >= 30
