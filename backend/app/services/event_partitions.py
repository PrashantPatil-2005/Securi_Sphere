"""Monthly partition management for the events table."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import text

from app.config import settings
from app.database import engine

logger = logging.getLogger(__name__)


def _month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    return start, end


def _partition_name(year: int, month: int) -> str:
    return f"events_y{year}m{month:02d}"


async def is_events_partitioned() -> bool:
    async with engine.connect() as conn:
        row = await conn.execute(
            text(
                "SELECT 1 FROM pg_partitioned_table WHERE partrelid = 'public.events'::regclass"
            )
        )
        return row.scalar() is not None


async def ensure_event_partitions(months_ahead: int = 3, months_back: int = 12) -> None:
    if not settings.event_partitioning_enabled:
        return
    if not await is_events_partitioned():
        logger.warning("Event partitioning enabled but events table is not partitioned yet")
        return

    now = datetime.now(timezone.utc)
    targets: list[tuple[int, int]] = []
    y, m = now.year, now.month
    for _ in range(months_back + months_ahead + 1):
        targets.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1

    async with engine.begin() as conn:
        for year, month in sorted(set(targets)):
            name = _partition_name(year, month)
            start, end = _month_bounds(year, month)
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE IF NOT EXISTS {name}
                    PARTITION OF events
                    FOR VALUES FROM (:start) TO (:end)
                    """
                ),
                {"start": start, "end": end},
            )
    logger.info("Event partitions ensured (%d months)", len(targets))


async def drop_old_event_partitions(cutoff: datetime) -> int:
    """Detach and drop monthly partitions wholly before cutoff month."""
    if not settings.event_partitioning_enabled or not await is_events_partitioned():
        return 0

    dropped = 0
    async with engine.begin() as conn:
        rows = await conn.execute(
            text(
                """
                SELECT c.relname AS name
                FROM pg_inherits i
                JOIN pg_class c ON c.oid = i.inhrelid
                JOIN pg_class p ON p.oid = i.inhparent
                WHERE p.relname = 'events' AND c.relname LIKE 'events_y%'
                """
            )
        )
        for (name,) in rows.fetchall():
            if name == "events_default":
                continue
            try:
                year = int(name[8:12])
                month = int(name[13:15])
            except (ValueError, IndexError):
                continue
            _, part_end = _month_bounds(year, month)
            if part_end <= cutoff:
                await conn.execute(text(f"DROP TABLE IF EXISTS {name}"))
                dropped += 1
    if dropped:
        logger.info("Dropped %d old event partitions before %s", dropped, cutoff.date())
    return dropped
