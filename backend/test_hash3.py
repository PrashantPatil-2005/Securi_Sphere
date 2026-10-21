import asyncio
import sys
import json
from uuid import UUID
from datetime import datetime, timezone
from app.database import async_session
from app.models.audit import AuditLog
from app.services.audit_chain import hash_audit_log, entry_payload, _normalize

async def main():
    async with async_session() as db:
        from sqlalchemy import select
        # Get a range of entries
        result = await db.execute(select(AuditLog).where(AuditLog.chain_seq >= 1).where(AuditLog.chain_seq <= 20).order_by(AuditLog.chain_seq.asc()))
        entries = result.scalars().all()
        
        print(f"Checking {len(entries)} entries (seq 1-20)")
        print("=" * 80)
        
        for e in entries:
            # Build payload the same way as entry_payload
            body = {
                "chain_seq": e.chain_seq,
                "id": str(e.id),
                "user_id": _normalize(e.user_id),
                "action": e.action,
                "resource_type": e.resource_type,
                "resource_id": _normalize(e.resource_id),
                "ip_address": str(e.ip_address) if e.ip_address else None,
                "details": e.details,
                "timestamp": e.timestamp.isoformat(),
                "prev_hash": e.prev_hash,
            }
            constructed_payload = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
            constructed_hash = __import__('hashlib').sha256(constructed_payload.encode('utf-8')).hexdigest()
            
            # Use actual entry_payload function
            actual_payload = entry_payload(
                chain_seq=e.chain_seq,
                entry_id=e.id,
                user_id=e.user_id,
                action=e.action,
                resource_type=e.resource_type,
                resource_id=e.resource_id,
                ip_address=str(e.ip_address) if e.ip_address else None,
                details=e.details,
                timestamp_iso=e.timestamp.isoformat(),
                prev_hash=e.prev_hash,
            )
            actual_hash = __import__('hashlib').sha256(actual_payload.encode('utf-8')).hexdigest()
            
            payloads_match = constructed_payload == actual_payload
            
            print(f"Seq {e.chain_seq}: action={e.action}")
            print(f"  stored_hash: {e.entry_hash[:16]}...")
            print(f"  computed_hash: {actual_hash[:16]}...")
            print(f"  match: {e.entry_hash == actual_hash}")
            print(f"  payloads_equal: {payloads_match}")
            if e.details is not None:
                print(f"  details type: {type(e.details)}, value: {e.details}")
            else:
                print(f"  details: None")
            if e.ip_address is not None:
                print(f"  ip_address: {e.ip_address} (type: {type(e.ip_address)})")
            print()

asyncio.run(main())