from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event


async def check_suspicious_login(db, host, create_alert_fn) -> None:
    now = datetime.now(timezone.utc)
    fail_since = now - timedelta(minutes=10)
    success_since = now - timedelta(minutes=15)

    fail_count = await db.execute(
        select(func.count()).select_from(Event).where(
            Event.host_id == host.id,
            Event.event_type == "ssh_login_failure",
            Event.timestamp >= fail_since,
        )
    )
    if fail_count.scalar_one() < 3:
        return

    success_count = await db.execute(
        select(func.count()).select_from(Event).where(
            Event.host_id == host.id,
            Event.event_type == "ssh_login_success",
            Event.timestamp >= success_since,
        )
    )
    if success_count.scalar_one() >= 1:
        await create_alert_fn(
            db,
            host.id,
            "Suspicious Activity",
            "Successful login detected after multiple failed login attempts",
            "critical",
            None,
        )
