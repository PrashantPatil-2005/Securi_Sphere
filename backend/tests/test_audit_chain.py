"""Unit tests for audit hash chain."""

from datetime import datetime, timezone
from uuid import uuid4

from app.models.audit import AuditLog
from app.services.audit_chain import (
    GENESIS_HASH,
    compute_entry_hash,
    hash_audit_log,
    verify_audit_entries,
)


def _entry(
    chain_seq: int,
    *,
    prev_hash: str = GENESIS_HASH,
    action: str = "login",
    entry_hash: str | None = None,
) -> AuditLog:
    entry_id = uuid4()
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    digest = entry_hash or compute_entry_hash(
        chain_seq=chain_seq,
        entry_id=entry_id,
        user_id=None,
        action=action,
        resource_type=None,
        resource_id=None,
        ip_address="127.0.0.1",
        details={"ok": True},
        timestamp_iso=timestamp.isoformat(),
        prev_hash=prev_hash,
    )
    return AuditLog(
        id=entry_id,
        chain_seq=chain_seq,
        prev_hash=prev_hash,
        entry_hash=digest,
        action=action,
        ip_address="127.0.0.1",
        details={"ok": True},
        timestamp=timestamp,
    )


def test_verify_empty_chain():
    result = verify_audit_entries([])
    assert result.valid is True
    assert result.entries_checked == 0


def test_verify_valid_chain():
    first = _entry(1)
    second = _entry(2, prev_hash=first.entry_hash, action="logout")
    result = verify_audit_entries([first, second])
    assert result.valid is True
    assert result.entries_checked == 2
    assert result.chain_head_hash == second.entry_hash
    assert result.latest_chain_seq == 2


def test_verify_detects_tampered_hash():
    first = _entry(1)
    tampered = _entry(2, prev_hash=first.entry_hash, entry_hash="deadbeef" * 8)
    result = verify_audit_entries([first, tampered])
    assert result.valid is False
    assert result.failure is not None
    assert result.failure.reason == "entry_hash_mismatch"
    assert result.failure.chain_seq == 2


def test_hash_audit_log_matches_compute():
    entry = _entry(1)
    assert hash_audit_log(entry, GENESIS_HASH) == entry.entry_hash
