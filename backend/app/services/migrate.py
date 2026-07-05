"""Apply schema via Alembic (replaces legacy migrate.py loops)."""

import asyncio
import logging

from app.config import settings
from app.services.alembic_runner import upgrade_head_async
from app.services.event_partitions import ensure_event_partitions

logger = logging.getLogger(__name__)


async def migrate_schema() -> None:
    await upgrade_head_async()
    if settings.event_partitioning_enabled:
        await ensure_event_partitions()
    logger.info("Schema migration complete (alembic head)")


if __name__ == "__main__":
    asyncio.run(migrate_schema())
