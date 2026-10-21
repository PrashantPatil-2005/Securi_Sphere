import asyncio
import sys
import json
sys.path.insert(0, '.')
from sqlalchemy import select
from app.database import async_session
from app.models.audit import AuditLog
from app.services.audit import log_audit
from app.services.audit_chain import verify_audit_chain, hash_audit_log, entry_payload

async def main():
    async with async_session() as db:
        # Log a new audit entry
        await log_audit(db, "test_new_entry", ip_address="127.0.0.1")
        await db.commit()
        
        # Check the entry
        result = await db.execute(select(AuditLog).order_by(AuditLog.chain_seq.desc()).limit(1))
        entry = result.scalar_one()
        
        print(f"New entry: seq={entry.chain_seq}, action={entry.action}")
        print(f"  stored entry_hash: {entry.entry_hash}")
        print(f"  details: {entry.details}")
        print(f"  ip_address: {entry.ip_address}")
        print(f"  prev_hash: {entry.prev_hash}")
        
        # Verify the chain
        verification = await verify_audit_chain(db, limit=None, from_seq=None)
        print(f"\nChain verification:")
        print(f"  valid: {verification.valid}")
        print(f"  entries_checked: {verification.entries_checked}")
        print(f"  latest_chain_seq: {verification.latest_chain_seq}")
        print(f"  window_complete: {verification.window_complete}")
        if verification.failure:
            print(f"  failure: {verification.failure.reason} at seq {verification.failure.chain_seq}")
        
        # Also test the hash directly
        expected = hash_audit_log(entry, entry.prev_hash)
        print(f"\nDirect hash check:")
        print(f"  expected: {expected[:16]}...")
        print(f"  stored: {entry.entry_hash[:16]}...")
        print(f"  match: {entry.entry_hash == expected}")
        
        # Show the payload
        payload = entry_payload(
            chain_seq=entry.chain_seq,
            entry_id=entry.id,
            user_id=entry.user_id,
            action=entry.action,
            resource_type=entry.resource_type,
            resource_id=entry.resource_id,
            ip_address=str(entry.ip_address) if entry.ip_address else None,
            details=entry.details,
            timestamp_iso=entry.timestamp.isoformat(),
            prev_hash=entry.prev_hash,
        )
        print(f"\nPayload: {payload}")

asyncio.run(main())