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
    details: dict | None = None,
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
        details=details,
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
        details=details,
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


def test_verify_detects_prev_hash_mismatch():
    first = _entry(1)
    # Tamper with prev_hash of second entry
    tampered = _entry(2, prev_hash="0000000000000000000000000000000000000000000000000000000000000000", action="logout")
    result = verify_audit_entries([first, tampered])
    assert result.valid is False
    assert result.failure is not None
    assert result.failure.reason == "prev_hash_mismatch"
    assert result.failure.chain_seq == 2


def test_verify_entry_hash_mismatch_with_details_none():
    """Test that entries with details=None have consistent hashes."""
    first = _entry(1, details=None)
    second = _entry(2, prev_hash=first.entry_hash, action="logout", details=None)
    result = verify_audit_entries([first, second])
    assert result.valid is True
    assert result.entries_checked == 2


def test_verify_entry_hash_mismatch_with_details_dict():
    """Test that entries with details={} have consistent hashes."""
    first = _entry(1, details={})
    second = _entry(2, prev_hash=first.entry_hash, action="logout", details={})
    result = verify_audit_entries([first, second])
    assert result.valid is True
    assert result.entries_checked == 2


def test_verify_mixed_details():
    """Test chain with mixed details None and dict entries."""
    first = _entry(1, details=None)
    second = _entry(2, prev_hash=first.entry_hash, action="logout", details={"status": "ok"})
    result = verify_audit_entries([first, second])
    assert result.valid is True
    assert result.entries_checked == 2


def test_verify_long_chain():
    """Test verification of a long chain of entries."""
    entries = []
    prev = GENESIS_HASH
    for i in range(1, 51):
        entry = _entry(i, prev_hash=prev, action=f"action_{i}", details={"index": i})
        entries.append(entry)
        prev = entry.entry_hash
    
    result = verify_audit_entries(entries)
    assert result.valid is True
    assert result.entries_checked == 50
    assert result.latest_chain_seq == 50
    assert result.chain_head_hash == prev


def test_verify_tampered_middle_entry():
    """Test that tampering with a middle entry is detected."""
    first = _entry(1)
    second = _entry(2, prev_hash=first.entry_hash, action="logout")
    third = _entry(3, prev_hash=second.entry_hash, action="login")
    # Tamper with the third entry's hash
    tampered_third = _entry(3, prev_hash=second.entry_hash, action="login", entry_hash="tampered" * 8)
    result = verify_audit_entries([first, second, tampered_third])
    assert result.valid is False
    assert result.failure is not None
    assert result.failure.reason == "entry_hash_mismatch"
    assert result.failure.chain_seq == 3
    # Should have checked 2 entries before the mismatch
    assert result.entries_checked == 2


def test_verify_tampered_first_entry_after_genesis():
    """Test tampering with the second entry (first after genesis)."""
    first = _entry(1)
    second = _entry(2, prev_hash=first.entry_hash, action="logout", entry_hash="deadbeef" * 8)
    result = verify_audit_entries([first, second])
    assert result.valid is False
    assert result.failure.chain_seq == 2
    assert result.entries_checked == 1


def test_hash_audit_log_matches_compute():
    entry = _entry(1)
    assert hash_audit_log(entry, GENESIS_HASH) == entry.entry_hash


def test_hash_audit_log_different_details_serialization():
    """Test that different details values produce different hashes."""
    entry_none = _entry(1, details=None)
    entry_dict = _entry(2, details={"status": "ok"})
    
    hash_none = hash_audit_log(entry_none, GENESIS_HASH)
    hash_dict = hash_audit_log(entry_dict, GENESIS_HASH)
    
    assert hash_none != hash_dict
    # details=None produces "details":null, details={"status":"ok"} produces "details":{"status":"ok"}


def test_verify_entries_stops_at_first_mismatch():
    """Test that verification stops at the first mismatch and reports correct count."""
    first = _entry(1)
    # Second entry has wrong hash
    second = _entry(2, prev_hash=first.entry_hash, action="logout", entry_hash="wrong" * 8)
    # Third entry would be valid if chain continued
    third = _entry(3, prev_hash=second.entry_hash, action="login")
    
    result = verify_audit_entries([first, second, third])
    assert result.valid is False
    assert result.entries_checked == 1  # Only the first entry was verified
    assert result.failure.chain_seq == 2
    assert result.failure.reason == "entry_hash_mismatch"


def test_verify_partial_window():
    """Test that window_complete is False when chain doesn't extend to max_seq."""
    first = _entry(1)
    second = _entry(2, prev_hash=first.entry_hash, action="logout")
    
    result = verify_audit_entries([first, second])
    assert result.valid is True
    assert result.entries_checked == 2
    assert result.window_complete is True