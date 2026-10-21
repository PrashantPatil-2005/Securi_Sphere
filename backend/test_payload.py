import asyncio
import sys
import json
from uuid import UUID
from datetime import datetime, timezone
from app.database import async_session
from app.models.audit import AuditLog
from app.services.audit_chain import entry_payload, _normalize

async def main():
    async with async_session() as db:
        from sqlalchemy import select
        
        # Check entry 1919 with details as dict
        result = await db.execute(select(AuditLog).where(AuditLog.chain_seq == 1919))
        e1919 = result.scalar_one()
        
        # Check entry around 1920 with details=None
        result = await db.execute(select(AuditLog).where(AuditLog.chain_seq == 1920))
        e1920 = result.scalar_one()
        
        print("=== Entry 1919 (details=dict) ===")
        print(f"details: {e1919.details} (type: {type(e1919.details)})")
        
        # Build payload manually
        body = {
            "chain_seq": e1919.chain_seq,
            "id": str(e1919.id),
            "user_id": _normalize(e1919.user_id),
            "action": e1919.action,
            "resource_type": e1919.resource_type,
            "resource_id": _normalize(e1919.resource_id),
            "ip_address": str(e1919.ip_address) if e1919.ip_address else None,
            "details": e1919.details,
            "timestamp": e1919.timestamp.isoformat(),
            "prev_hash": e1919.prev_hash,
        }
        manual_payload = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
        print(f"manual payload: {manual_payload}")
        manual_hash = __import__('hashlib').sha256(manual_payload.encode('utf-8')).hexdigest()
        print(f"manual hash: {manual_hash}")
        print(f"stored hash: {e1919.entry_hash}")
        print(f"match: {e1919.entry_hash == manual_hash}")
        
        # Use actual entry_payload function
        actual_payload = entry_payload(
            chain_seq=e1919.chain_seq,
            entry_id=e1919.id,
            user_id=e1919.user_id,
            action=e1919.action,
            resource_type=e1919.resource_type,
            resource_id=e1919.resource_id,
            ip_address=str(e1919.ip_address) if e1919.ip_address else None,
            details=e1919.details,
            timestamp_iso=e1919.timestamp.isoformat(),
            prev_hash=e1919.prev_hash,
        )
        actual_hash = __import__('hashlib').sha256(actual_payload.encode('utf-8')).hexdigest()
        print(f"\\nactual entry_payload: {actual_payload}")
        print(f"actual hash: {actual_hash}")
        print(f"match with entry_payload: {e1919.entry_hash == actual_hash}")
        print(f"payloads equal: {manual_payload == actual_payload}")
        
        print()
        print("=== Entry 1920 (details=None) ===")
        print(f"details: {e1920.details} (type: {type(e1920.details)})")
        
        body2 = {
            "chain_seq": e1920.chain_seq,
            "id": str(e1920.id),
            "user_id": _normalize(e1920.user_id),
            "action": e1920.action,
            "resource_type": e1920.resource_type,
            "resource_id": _normalize(e1920.resource_id),
            "ip_address": str(e1920.ip_address) if e1920.ip_address else None,
            "details": e1920.details,
            "timestamp": e1920.timestamp.isoformat(),
            "prev_hash": e1920.prev_hash,
        }
        manual_payload2 = json.dumps(body2, sort_keys=True, separators=(",", ":"), default=str)
        print(f"manual payload: {manual_payload2}")
        manual_hash2 = __import__('hashlib').sha256(manual_payload2.encode('utf-8')).hexdigest()
        print(f"manual hash: {manual_hash2}")
        print(f"stored hash: {e1920.entry_hash}")
        print(f"match: {e1920.entry_hash == manual_hash2}")
        
        actual_payload2 = entry_payload(
            chain_seq=e1920.chain_seq,
            entry_id=e1920.id,
            user_id=e1920.user_id,
            action=e1920.action,
            resource_type=e1920.resource_type,
            resource_id=e1920.resource_id,
            ip_address=str(e1920.ip_address) if e1920.ip_address else None,
            details=e1920.details,
            timestamp_iso=e1920.timestamp.isoformat(),
            prev_hash=e1920.prev_hash,
        )
        actual_hash2 = __import__('hashlib').sha256(actual_payload2.encode('utf-8')).hexdigest()
        print(f"actual entry_payload: {actual_payload2}")
        print(f"actual hash: {actual_hash2}")
        print(f"match with entry_payload: {e1920.entry_hash == actual_hash2}")
        print(f"payloads equal: {manual_payload2 == actual_payload2}")

asyncio.run(main())