import asyncio
import sys
sys.path.insert(0, '.')
from app.database import async_session
from app.models.audit import AuditLog

async def main():
    async with async_session() as db:
        from sqlalchemy import select, func
        # Get count
        result = await db.execute(select(AuditLog).order_by(AuditLog.chain_seq.desc()).limit(1))
        last = result.scalars().first()
        print(f'Last entry: seq={last.chain_seq}, action={last.action}')
        
        # Get entries around 1910
        result = await db.execute(select(AuditLog).where(AuditLog.chain_seq >= 1908).where(AuditLog.chain_seq <= 1912).order_by(AuditLog.chain_seq.asc()))
        entries = result.scalars().all()
        for e in entries:
            print(f'Seq {e.chain_seq}: action={e.action}, ts={e.timestamp.isoformat()}, prev={e.prev_hash[:16]}..., entry_hash={e.entry_hash[:16]}...')
            
            # Compute expected hash
            from app.services.audit_chain import hash_audit_log
            expected = hash_audit_log(e, e.prev_hash)
            match = e.entry_hash == expected
            print(f'  Expected: {expected[:16]}..., Match: {match}')
            if not match:
                print(f'  DETAILS: e.details={e.details}')
                print(f'  e.ip_address={e.ip_address}')
                print(f'  e.user_id={e.user_id}')
                print(f'  e.resource_id={e.resource_id}')

asyncio.run(main())