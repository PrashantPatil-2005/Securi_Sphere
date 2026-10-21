import asyncio
import sys
sys.path.insert(0, '.')
from app.database import async_session
from app.models.audit import AuditLog
from app.services.audit_chain import hash_audit_log

async def main():
    async with async_session() as db:
        from sqlalchemy import select
        result = await db.execute(select(AuditLog).where(AuditLog.chain_seq == 1910))
        entry = result.scalar_one()
        expected = hash_audit_log(entry, entry.prev_hash)
        print(f'entry_hash: {entry.entry_hash}')
        print(f'expected: {expected}')
        print(f'match: {entry.entry_hash == expected}')

asyncio.run(main())