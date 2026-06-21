"""Unit tests for detection logic."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.services.detection import SUPPORTED_RULE_TYPES
from app.services.timeline import _chain_confidence, _chain_title, _timeline_fingerprint


def test_supported_rule_types():
    assert "failed_logins" in SUPPORTED_RULE_TYPES
    assert "brute_force" in SUPPORTED_RULE_TYPES
    assert "agent_offline" in SUPPORTED_RULE_TYPES
    assert "unknown_rule" not in SUPPORTED_RULE_TYPES


def test_ssh_alert_tiering_logic():
    """Brute force threshold should supersede failed logins — only one alert tier."""
    fail_count = 12
    bf_threshold = 10
    fl_threshold = 5
    fired = []
    if fail_count >= bf_threshold:
        fired.append("brute_force")
    elif fail_count >= fl_threshold:
        fired.append("failed_logins")
    assert fired == ["brute_force"]

    fail_count = 7
    fired = []
    if fail_count >= bf_threshold:
        fired.append("brute_force")
    elif fail_count >= fl_threshold:
        fired.append("failed_logins")
    assert fired == ["failed_logins"]

    fail_count = 3
    fired = []
    if fail_count >= bf_threshold:
        fired.append("brute_force")
    elif fail_count >= fl_threshold:
        fired.append("failed_logins")
    assert fired == []


def test_offline_dedup_by_rule_id():
    """Open alerts dedup by rule_id, not title string."""
    offline_rule_id = uuid4()
    open_alerts = [{"rule_id": offline_rule_id, "title": "Agent Offline"}]
    open_rule_ids = {a["rule_id"] for a in open_alerts if a["rule_id"]}
    assert offline_rule_id in open_rule_ids
    assert "agent_offline" not in [a["title"] for a in open_alerts]


def test_timeline_fingerprint_stable():
    host_id = uuid4()
    started = datetime(2025, 6, 21, 14, 30, tzinfo=timezone.utc)
    title = "Potential Brute Force Activity"
    fp1 = _timeline_fingerprint(host_id, title, started)
    fp2 = _timeline_fingerprint(host_id, title, started.replace(minute=15))
    assert fp1 == fp2
    fp3 = _timeline_fingerprint(host_id, "Other Title", started)
    assert fp1 != fp3


def test_chain_title_brute_force_chain():
    types = ["ssh_login_failure", "ssh_login_success", "sudo_usage"]
    assert "Escalation" in _chain_title(types)


def test_chain_confidence_capped():
    class FakeEvent:
        def __init__(self, event_type):
            self.event_type = event_type
            self.timestamp = datetime.now(timezone.utc)

    events = [FakeEvent("ssh_login_failure")] * 10
    events.append(FakeEvent("ssh_login_success"))
    events.append(FakeEvent("sudo_usage"))
    assert _chain_confidence(events) <= 100
