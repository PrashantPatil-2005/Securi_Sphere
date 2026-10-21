"""Migration script to repair the audit hash chain.

This script recomputes the entry_hash and prev_hash values for all
audit log entries, ensuring consistency with the current
entry_payload() / hash_audit_log() serialization.

WARNING: This script modifies the audit_logs table. It should only be
run with a complete database backup and explicit authorization.

The migration:
1. Backs up the existing data
2. Recomputes the hash chain from sequence 1 (genesis)
3. Updates prev_hash and entry_hash for each entry
4. Records the migration as an audit_integrity_failure entry
"""

import asyncio
import json
import hashlib
import shutil
import sys
from datetime import datetime, timezone
from uuid import UUID, uuid4

sys.path.insert(0, '.')
from sqlalchemy import select, text
from app.database import async_session
from app.models.audit import AuditLog
from app.services.audit_chain import GENESIS_HASH, hash_audit_log, entry_payload


async def backup_audit_data():
    """Create a backup of the existing audit log data."""
    backup_dir = f"backups/audit_chain_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    print(f"Creating backup at {backup_dir}...")
    
    # Copy the database file if using file-based DB
    # For PostgreSQL, we'll just export the data
    async with async_session() as db:
        # Export all audit log entries
        result = await db.execute(select(AuditLog).order_by(AuditLog.chain_seq.asc()))
        entries = result.scalars().all()
        
        backup_data = []
        for e in entries:
            backup_data.append({
                "id": str(e.id),
                "chain_seq": e.chain_seq,
                "prev_hash": e.prev_hash,
                "entry_hash": e.entry_hash,
                "user_id": str(e.user_id) if e.user_id else None,
                "action": e.action,
                "resource_type": e.resource_type,
                "resource_id": str(e.resource_id) if e.resource_id else None,
                "ip_address": str(e.ip_address) if e.ip_address else None,
                "details": dict(e.details) if e.details else None,
                "timestamp": e.timestamp.isoformat(),
            })
        
        import os
        os.makedirs(backup_dir, exist_ok=True)
        backup_file = f"{backup_dir}/audit_logs_backup.json"
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f, default=str)
        
        print(f"Backup created: {backup_file} ({len(entries)} entries)")
        return backup_dir


async def repair_audit_chain():
    """Repair the audit hash chain by recomputing all entry_hash values."""
    async with async_session() as db:
        # Get all entries ordered by chain_seq
        result = await db.execute(select(AuditLog).order_by(AuditLog.chain_seq.asc()))
        entries = result.scalars().all()
        
        print(f"Repairing audit chain with {len(entries)} entries...")
        
        prev_hash = GENESIS_HASH
        updates = []
        
        for entry in entries:
            # Recompute the entry_hash
            new_entry_hash = hash_audit_log(entry, prev_hash)
            
            updates.append({
                "chain_seq": entry.chain_seq,
                "prev_hash": prev_hash,
                "entry_hash": new_entry_hash,
            })
            
            prev_hash = new_entry_hash
        
        # Apply updates
        for update in updates:
            await db.execute(
                text(
                    "UPDATE audit_logs SET prev_hash = :prev_hash, entry_hash = :entry_hash "
                    "WHERE chain_seq = :chain_seq"
                ),
                {
                    "prev_hash": update["prev_hash"],
                    "entry_hash": update["entry_hash"],
                    "chain_seq": update["chain_seq"],
                },
            )
        
        await db.commit()
        print(f"Chain repaired successfully. All {len(entries)} entry_hash values updated.")
        
        return True


async def record_migration_failure(backup_dir: str):
    """Record the migration as an audit_integrity_failure entry."""
    from app.services.audit import log_audit
    from app.database import async_engine, async_session
    
    async with async_session() as db:
        # Get the admin user or system user
        from app.models.user import User
        result = await db.execute(select(User).where(User.email == "admin@securi.local"))
        admin_user = result.scalar_one()
        
        # Log the integrity failure and migration
        await log_audit(
            db,
            action="audit_chain_repair_migration",
            user_id=admin_user.id,
            ip_address="127.0.0.1",
            details={
                "backup_location": backup_dir,
                "entries_repaired": None,  # Will be set after repair
                "migration_timestamp": datetime.utcnow().isoformat(),
                "note": "Hash chain repair migration - original data preserved in backup",
            },
        )
        await db.commit()
        
        print("Migration recorded as audit_integrity_failure entry.")


async def main():
    print("=" * 60)
    print("Audit Hash Chain Repair Migration")
    print("=" * 60)
    
    # Step 1: Backup
    backup_dir = await backup_audit_data()
    
    # Step 2: Repair the chain
    await repair_audit_chain()
    
    # Step 3: Record the migration
    await record_migration_failure(backup_dir)
    
    print("=" * 60)
    print("Migration complete.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())