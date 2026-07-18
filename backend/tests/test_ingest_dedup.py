"""Tests for event ingest deduplication."""

import hashlib
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ingest_dedup import event_fingerprint


def test_event_fingerprint_deterministic():
    ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    fp1 = event_fingerprint("host-1", ts, "ssh_login_failure", "Failed password for root")
    fp2 = event_fingerprint("host-1", ts, "ssh_login_failure", "Failed password for root")
    assert fp1 == fp2


def test_event_fingerprint_differs_on_host():
    ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    fp1 = event_fingerprint("host-1", ts, "ssh_login_failure", "log")
    fp2 = event_fingerprint("host-2", ts, "ssh_login_failure", "log")
    assert fp1 != fp2


def test_event_fingerprint_differs_on_type():
    ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    fp1 = event_fingerprint("host-1", ts, "ssh_login_failure", "log")
    fp2 = event_fingerprint("host-1", ts, "ssh_login_success", "log")
    assert fp1 != fp2


def test_event_fingerprint_differs_on_raw_log():
    ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    fp1 = event_fingerprint("host-1", ts, "ssh_login_failure", "log A")
    fp2 = event_fingerprint("host-1", ts, "ssh_login_failure", "log B")
    assert fp1 != fp2


def test_event_fingerprint_differs_on_timestamp():
    ts1 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    ts2 = datetime(2026, 1, 1, 12, 0, 1, tzinfo=timezone.utc)
    fp1 = event_fingerprint("host-1", ts1, "ssh_login_failure", "log")
    fp2 = event_fingerprint("host-1", ts2, "ssh_login_failure", "log")
    assert fp1 != fp2


def test_event_fingerprint_handles_none_raw_log():
    ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    fp = event_fingerprint("host-1", ts, "ssh_login_failure", None)
    assert len(fp) == 64  # SHA-256 hex digest


def test_event_fingerprint_is_sha256():
    ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    fp = event_fingerprint("host-1", ts, "ssh_login_failure", "test")
    expected = hashlib.sha256(
        f"host-1:{ts.isoformat()}:ssh_login_failure:test".encode()
    ).hexdigest()
    assert fp == expected
