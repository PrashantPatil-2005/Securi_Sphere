import sys
sys.path.insert(0, '.')
import asyncio
from sqlalchemy import select
from app.database import async_session
from app.models.audit import AuditLog

async def main():
    async with async_session() as db:
        max_seq = (await db.execute(select(AuditLog.chain_seq).order_by(AuditLog.chain_seq.desc()).limit(1))).scalar_one()
        print(f'Max chain_seq: {max_seq}')
        
        result = await db.execute(select(AuditLog).where(AuditLog.chain_seq >= 1905).where(AuditLog.chain_seq <= 1915).order_by(AuditLog.chain_seq.asc()))
        entries = result.scalars().all()
        for e in entries:
            print(f'Seq {e.chain_seq}: action={e.action}, prev_hash={e.prev_hash[:16]}..., entry_hash={e.entry_hash[:16]}...')
            from app.services.audit_chain import hash_audit_log
            expected = hash_audit_log(e, e.prev_hash)
            print(f'  Expected hash: {expected[:16]}...')
            print(f'  Match: {e.entry_hash == expected}')
            print()

asyncio.run(main())