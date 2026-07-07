import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.services.audit_chain import GENESIS_HASH, AUDIT_CHAIN_LOCK_KEY, hash_audit_log


async def _next_chain_seq(db: AsyncSession) -> int:
    result = await db.execute(text("SELECT nextval('audit_logs_chain_seq_seq')"))
    return int(result.scalar_one())


async def _reserve_chain_slot(db: AsyncSession) -> tuple[int, str]:
    await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": AUDIT_CHAIN_LOCK_KEY})
    chain_seq = await _next_chain_seq(db)
    row = (
        await db.execute(
            text("SELECT entry_hash FROM audit_logs ORDER BY chain_seq DESC LIMIT 1")
        )
    ).first()
    prev_hash = row[0] if row else GENESIS_HASH
    return chain_seq, prev_hash


async def log_audit(
    db: AsyncSession,
    action: str,
    user_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: uuid.UUID | None = None,
    ip_address: str | None = None,
    details: dict | None = None,
) -> None:
    timestamp = datetime.now(timezone.utc)
    chain_seq, prev_hash = await _reserve_chain_slot(db)
    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        details=details,
        timestamp=timestamp,
        chain_seq=chain_seq,
        prev_hash=prev_hash,
    )
    entry.entry_hash = hash_audit_log(entry, prev_hash)
    db.add(entry)
