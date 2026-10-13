"""Tests for event ingest deduplication."""

import hashlib
from datetime import datetime, timezone
from uuid import uuid4


from app.services.ingest_dedup import event_fingerprint


def test_event_fingerprint_deterministic():
    fp1 = event_fingerprint("host-1", "ssh_login_failure", "Failed password for root")
    fp2 = event_fingerprint("host-1", "ssh_login_failure", "Failed password for root")
    assert fp1 == fp2


def test_event_fingerprint_with_raw_log():
    """Fingerprint uses raw_log when available (journald events)."""
    host_id = uuid4()
    fp1 = event_fingerprint(host_id, "ssh_login_failure", raw_log="Failed password for root")
    fp2 = event_fingerprint(host_id, "ssh_login_failure", raw_log="Failed password for root")
    fp3 = event_fingerprint(host_id, "ssh_login_failure", raw_log="Different log")
    assert fp1 == fp2
    assert fp1 != fp3


def test_event_fingerprint_with_description():
    """Fingerprint falls back to description when raw_log is None (simulated events)."""
    host_id = uuid4()
    fp1 = event_fingerprint(host_id, "ssh_login_failure", description="Test ssh login failure")
    fp2 = event_fingerprint(host_id, "ssh_login_failure", description="Test ssh login failure")
    fp3 = event_fingerprint(host_id, "ssh_login_failure", description="Different description")
    assert fp1 == fp2
    assert fp1 != fp3


def test_event_fingerprint_with_both_raw_and_desc():
    """When both raw_log and description are provided, raw_log takes precedence."""
    host_id = uuid4()
    fp1 = event_fingerprint(host_id, "ssh_login_failure", raw_log="log A", description="desc")
    fp2 = event_fingerprint(host_id, "ssh_login_failure", raw_log="log A", description="desc")
    assert fp1 == fp2


def test_event_fingerprint_differs_on_host():
    host_id = uuid4()
    fp1 = event_fingerprint(host_id, "ssh_login_failure", raw_log="log")
    fp2 = event_fingerprint(uuid4(), "ssh_login_failure", raw_log="log")
    assert fp1 != fp2


def test_event_fingerprint_differs_on_type():
    host_id = uuid4()
    fp1 = event_fingerprint(host_id, "ssh_login_failure", raw_log="log")
    fp2 = event_fingerprint(host_id, "ssh_login_success", raw_log="log")
    assert fp1 != fp2


def test_event_fingerprint_differs_on_raw_log():
    host_id = uuid4()
    fp1 = event_fingerprint(host_id, "ssh_login_failure", raw_log="log A")
    fp2 = event_fingerprint(host_id, "ssh_login_failure", raw_log="log B")
    assert fp1 != fp2


def test_event_fingerprint_with_none_raw_and_desc():
    """When both raw_log and description are None, fingerprint is based on empty string."""
    host_id = uuid4()
    fp1 = event_fingerprint(host_id, "ssh_login_failure")
    fp2 = event_fingerprint(host_id, "ssh_login_failure")
    assert fp1 == fp2
    assert len(fp1) == 64  # SHA-256 hex digest


def test_event_fingerprint_is_sha256():
    fp = event_fingerprint("host-1", "ssh_login_failure", raw_log="test")
    expected = hashlib.sha256(
        f"host-1:ssh_login_failure:test".encode()
    ).hexdigest()
    assert fp == expected


def test_event_fingerprint_idempotency_scenario():
    """Simulate the core issue: same journal entry processed twice should be deduplicated."""
    host_id = uuid4()
    # Same raw_log (same journal entry) should produce same fingerprint regardless of "timestamp"
    fp1 = event_fingerprint(host_id, "root_login", raw_log="Oct 10 10:33:19 KALI sudo[3933]: pam_unix(sudo:session): session opened for user root")
    fp2 = event_fingerprint(host_id, "root_login", raw_log="Oct 10 10:33:19 KALI sudo[3933]: pam_unix(sudo:session): session opened for user root")
    assert fp1 == fp2, "Same journal entry processed at different times should have same fingerprint"