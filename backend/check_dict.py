import asyncio
import sys
sys.path.insert(0, '.')
from app.database import async_session
from app.models.audit import AuditLog
from app.services.audit_chain import hash_audit_log

async def main():
    async with async_session() as db:
        from sqlalchemy import select
        # Check entry 1919
        result = await db.execute(select(AuditLog).where(AuditLog.chain_seq == 1919))
        e = result.scalar_one()
        print(f'Seq 1919: action={e.action}, details={e.details}, type={type(e.details)}')
        expected = hash_audit_log(e, e.prev_hash)
        print(f'  stored_hash: {e.entry_hash[:16]}...')
        print(f'  computed_hash: {expected[:16]}...')
        print(f'  match: {e.entry_hash == expected}')
        
        # Check entry 1 (if it exists)
        result = await db.execute(select(AuditLog).where(AuditLog.chain_seq == 1))
        e1 = result.scalar_one()
        print(f'\\nSeq 1: action={e1.action}, details={e1.details}, type={type(e1.details)}')
        expected1 = hash_audit_log(e1, e1.prev_hash)
        print(f'  stored_hash: {e1.entry_hash[:16]}...')
        print(f'  computed_hash: {expected1[:16]}...')
        print(f'  match: {e1.entry_hash == expected1}')

asyncio.run(main())