"""SHA-256 hash chain for tamper-evident audit logs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog

GENESIS_HASH = "0" * 64
AUDIT_CHAIN_LOCK_KEY = 420_015


def _normalize(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if value is None:
        return None
    return value


def entry_payload(
    *,
    chain_seq: int,
    entry_id: UUID,
    user_id: UUID | None,
    action: str,
    resource_type: str | None,
    resource_id: UUID | None,
    ip_address: str | None,
    details: dict | None,
    timestamp_iso: str,
    prev_hash: str,
) -> str:
    body = {
        "chain_seq": chain_seq,
        "id": str(entry_id),
        "user_id": _normalize(user_id),
        "action": action,
        "resource_type": resource_type,
        "resource_id": _normalize(resource_id),
        "ip_address": str(ip_address) if ip_address else None,
        "details": details,
        "timestamp": timestamp_iso,
        "prev_hash": prev_hash,
    }
    return json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)


def compute_entry_hash(
    *,
    chain_seq: int,
    entry_id: UUID,
    user_id: UUID | None,
    action: str,
    resource_type: str | None,
    resource_id: UUID | None,
    ip_address: str | None,
    details: dict | None,
    timestamp_iso: str,
    prev_hash: str,
) -> str:
    payload = entry_payload(
        chain_seq=chain_seq,
        entry_id=entry_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        details=details,
        timestamp_iso=timestamp_iso,
        prev_hash=prev_hash,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def hash_audit_log(entry: AuditLog, prev_hash: str) -> str:
    return compute_entry_hash(
        chain_seq=entry.chain_seq,
        entry_id=entry.id,
        user_id=entry.user_id,
        action=entry.action,
        resource_type=entry.resource_type,
        resource_id=entry.resource_id,
        ip_address=str(entry.ip_address) if entry.ip_address else None,
        details=entry.details,
        timestamp_iso=entry.timestamp.isoformat(),
        prev_hash=prev_hash,
    )


@dataclass
class AuditChainFailure:
    chain_seq: int
    reason: str
    expected: str | None = None
    actual: str | None = None


@dataclass
class AuditChainVerification:
    valid: bool
    entries_checked: int
    chain_head_hash: str | None
    latest_chain_seq: int | None
    failure: AuditChainFailure | None = None


def verify_audit_entries(entries: list[AuditLog]) -> AuditChainVerification:
    prev_hash = GENESIS_HASH
    if not entries:
        return AuditChainVerification(
            valid=True,
            entries_checked=0,
            chain_head_hash=None,
            latest_chain_seq=None,
        )

    for entry in entries:
        if entry.prev_hash != prev_hash:
            return AuditChainVerification(
                valid=False,
                entries_checked=0,
                chain_head_hash=None,
                latest_chain_seq=entry.chain_seq,
                failure=AuditChainFailure(
                    chain_seq=entry.chain_seq,
                    reason="prev_hash_mismatch",
                    expected=prev_hash,
                    actual=entry.prev_hash,
                ),
            )
        expected = hash_audit_log(entry, prev_hash)
        if entry.entry_hash != expected:
            return AuditChainVerification(
                valid=False,
                entries_checked=0,
                chain_head_hash=None,
                latest_chain_seq=entry.chain_seq,
                failure=AuditChainFailure(
                    chain_seq=entry.chain_seq,
                    reason="entry_hash_mismatch",
                    expected=expected,
                    actual=entry.entry_hash,
                ),
            )
        prev_hash = entry.entry_hash

    return AuditChainVerification(
        valid=True,
        entries_checked=len(entries),
        chain_head_hash=prev_hash,
        latest_chain_seq=entries[-1].chain_seq,
    )


async def fetch_audit_chain(
    db: AsyncSession,
    *,
    limit: int = 10_000,
    from_seq: int | None = None,
) -> list[AuditLog]:
    q: Select[tuple[AuditLog]] = select(AuditLog).order_by(AuditLog.chain_seq.asc())
    if from_seq is not None:
        q = q.where(AuditLog.chain_seq >= from_seq)
    q = q.limit(limit)
    return list((await db.execute(q)).scalars().all())


async def verify_audit_chain(
    db: AsyncSession,
    *,
    limit: int = 10_000,
    from_seq: int | None = None,
) -> AuditChainVerification:
    entries = await fetch_audit_chain(db, limit=limit, from_seq=from_seq)
    return verify_audit_entries(entries)
