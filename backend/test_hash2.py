import asyncio
import sys
import json
from uuid import UUID
from datetime import datetime, timezone
from app.database import async_session
from app.models.audit import AuditLog
from app.services.audit_chain import hash_audit_log, entry_payload, _normalize, GENESIS_HASH

def _normalize_value(value):
    if isinstance(value, UUID):
        return str(value)
    if value is None:
        return None
    return value

async def main():
    async with async_session() as db:
        from sqlalchemy import select
        result = await db.execute(select(AuditLog).where(AuditLog.chain_seq == 1910))
        entry = result.scalar_one()
        
        # Build payload the same way as entry_payload
        body = {
            "chain_seq": entry.chain_seq,
            "id": str(entry.id),
            "user_id": _normalize_value(entry.user_id),
            "action": entry.action,
            "resource_type": entry.resource_type,
            "resource_id": _normalize_value(entry.resource_id),
            "ip_address": str(entry.ip_address) if entry.ip_address else None,
            "details": entry.details,
            "timestamp": entry.timestamp.isoformat(),
            "prev_hash": entry.prev_hash,
        }
        payload = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
        print(f'Constructed payload: {payload}')
        
        # Compute hash from payload
        expected_hash = __import__('hashlib').sha256(payload.encode('utf-8')).hexdigest()
        print(f'Hash from payload: {expected_hash}')
        print(f'Stored entry_hash: {entry.entry_hash}')
        print(f'Match: {entry.entry_hash == expected_hash}')
        
        # Now try using the actual entry_payload function
        actual_payload = entry_payload(
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
        print(f'\\nActual entry_payload: {actual_payload}')
        actual_hash = __import__('hashlib').sha256(actual_payload.encode('utf-8')).hexdigest()
        print(f'Hash from entry_payload: {actual_hash}')
        print(f'Match with entry_payload: {entry.entry_hash == actual_hash}')
        
        # Compare payloads
        print(f'\\nPayloads equal: {payload == actual_payload}')
        
        # Debug: check each field
        print(f'\\n--- Field comparison ---')
        print(f'chain_seq: {entry.chain_seq}')
        print(f'id: {entry.id} == str: {str(entry.id)}')
        print(f'user_id: {entry.user_id} _normalize: {_normalize_value(entry.user_id)}')
        print(f'action: {entry.action}')
        print(f'resource_type: {entry.resource_type}')
        print(f'resource_id: {entry.resource_id} _normalize: {_normalize_value(entry.resource_id)}')
        print(f'ip_address: {entry.ip_address} str: {str(entry.ip_address) if entry.ip_address else None}')
        print(f'details: {entry.details}')
        print(f'timestamp: {entry.timestamp.isoformat()}')
        print(f'prev_hash: {entry.prev_hash}')

asyncio.run(main())