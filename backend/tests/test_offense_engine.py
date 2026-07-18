"""Tests for offense engine — grouping, risk escalation, timeline, dedup."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.offense_engine import (
    AUTH_EVENT_TYPES,
    OFFENSE_WINDOW,
    RISK_FROM_SEVERITY,
    RISK_RANK,
    _append_timeline_entry,
    _max_risk,
    _track_user,
)


# ---------------------------------------------------------------------------
# Pure helper tests (no DB needed)
# ---------------------------------------------------------------------------

def test_risk_from_severity_mapping():
    assert RISK_FROM_SEVERITY["critical"] == "critical"
    assert RISK_FROM_SEVERITY["high"] == "high"
    assert RISK_FROM_SEVERITY["info"] == "low"


def test_max_risk_picks_higher():
    assert _max_risk("critical", "low") == "critical"
    assert _max_risk("low", "critical") == "critical"
    assert _max_risk("medium", "medium") == "medium"


def test_max_risk_unknown_treated_as_zero():
    assert _max_risk("high", "unknown") == "high"
    assert _max_risk("unknown", "high") == "high"


def test_auth_event_types_complete():
    assert "ssh_login_failure" in AUTH_EVENT_TYPES
    assert "ssh_login_success" in AUTH_EVENT_TYPES
    assert "sudo_usage" in AUTH_EVENT_TYPES
    assert "root_login" in AUTH_EVENT_TYPES


def test_risk_rank_ordering():
    assert RISK_RANK["low"] < RISK_RANK["medium"] < RISK_RANK["high"] < RISK_RANK["critical"]


# ---------------------------------------------------------------------------
# _append_timeline_entry
# ---------------------------------------------------------------------------

def test_append_timeline_entry_creates_list():
    offense = SimpleNamespace(timeline=None)
    entry = {"type": "alert", "timestamp": "2026-01-01T00:00:00"}
    _append_timeline_entry(offense, entry)
    assert len(offense.timeline) == 1
    assert offense.timeline[0]["type"] == "alert"


def test_append_timeline_entry_sorts_by_timestamp():
    offense = SimpleNamespace(timeline=[
        {"type": "alert", "timestamp": "2026-01-01T12:00:00"},
    ])
    entry = {"type": "event", "timestamp": "2026-01-01T06:00:00"}
    _append_timeline_entry(offense, entry)
    assert offense.timeline[0]["type"] == "event"
    assert offense.timeline[1]["type"] == "alert"


def test_append_timeline_entry_caps_at_500():
    offense = SimpleNamespace(timeline=[
        {"type": "event", "timestamp": f"2026-01-01T{i:02d}:00:00"}
        for i in range(500)
    ])
    entry = {"type": "alert", "timestamp": "2026-01-02T00:00:00"}
    _append_timeline_entry(offense, entry)
    assert len(offense.timeline) == 500


# ---------------------------------------------------------------------------
# _track_user
# ---------------------------------------------------------------------------

def test_track_user_adds_new():
    offense = SimpleNamespace(related_users=[])
    _track_user(offense, "admin")
    assert offense.related_users == ["admin"]


def test_track_user_no_duplicate():
    offense = SimpleNamespace(related_users=["admin"])
    _track_user(offense, "admin")
    assert offense.related_users == ["admin"]


def test_track_user_ignores_none():
    offense = SimpleNamespace(related_users=[])
    _track_user(offense, None)
    assert offense.related_users == []


def test_track_user_ignores_empty_string():
    offense = SimpleNamespace(related_users=[])
    _track_user(offense, "")
    assert offense.related_users == []


# ---------------------------------------------------------------------------
# OFFENSE_WINDOW
# ---------------------------------------------------------------------------

def test_offense_window_is_30_minutes():
    assert OFFENSE_WINDOW == timedelta(minutes=30)
