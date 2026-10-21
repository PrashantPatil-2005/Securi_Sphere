import asyncio
import sys
sys.path.insert(0, '.')
from app.database import async_session
from app.models.audit import AuditLog
from app.services.audit_chain import hash_audit_log, entry_payload, _normalize

async def main():
    async with async_session() as db:
        from sqlalchemy import select, func
        # Get max seq
        result = await db.execute(select(func.max(AuditLog.chain_seq)))
        max_seq = result.scalar_one()
        print(f'Max chain_seq: {max_seq}')
        
        # Get first 20 entries
        result = await db.execute(select(AuditLog).order_by(AuditLog.chain_seq.asc()).limit(20))
        entries = result.scalars().all()
        print(f'First 20 entries:')
        for e in entries:
            print(f'  seq={e.chain_seq}, action={e.action}, details={e.details}')
        
        # Check hash for first entry
        print()
        print('Hash check for first entry:')
        e = entries[0]
        expected = hash_audit_log(e, e.prev_hash)
        print(f'  stored_hash: {e.entry_hash[:16]}...')
        print(f'  computed_hash: {expected[:16]}...')
        print(f'  match: {e.entry_hash == expected}')
        
        # Check hash for entry 1910
        print()
        print('Hash check for entry 1910:')
        result = await db.execute(select(AuditLog).where(AuditLog.chain_seq == 1910))
        e1910 = result.scalar_one()
        expected1910 = hash_audit_log(e1910, e1910.prev_hash)
        print(f'  stored_hash: {e1910.entry_hash[:16]}...')
        print(f'  computed_hash: {expected1910[:16]}...')
        print(f'  match: {e1910.entry_hash == expected1910}')

asyncio.run(main())