"""Check if a host is in an active maintenance window."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.maintenance import MaintenanceWindow


async def is_host_in_maintenance(db: AsyncSession, host_id) -> bool:
    now = datetime.now(timezone.utc)
    row = (
        await db.execute(
            select(MaintenanceWindow.id).where(
                MaintenanceWindow.host_id == host_id,
                MaintenanceWindow.starts_at <= now,
                MaintenanceWindow.ends_at >= now,
            ).limit(1)
        )
    ).scalar_one_or_none()
    return row is not None
