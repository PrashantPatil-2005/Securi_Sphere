"""Graceful shutdown orchestration."""

from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.core.shutdown import shutdown_state
from app.database import engine
from app.jobs.queue import JobQueue
from app.websocket.manager import ConnectionManager

logger = logging.getLogger(__name__)


async def shutdown_application(
    *,
    scheduler: AsyncIOScheduler,
    job_queue: JobQueue,
    ws_manager: ConnectionManager,
) -> None:
    """Drain work and release resources within the configured grace window."""
    shutdown_state.begin()
    logger.info("graceful shutdown started", extra={"grace_seconds": settings.shutdown_grace_seconds})

    if scheduler.running:
        scheduler.shutdown(wait=False)

    await ws_manager.stop()

    try:
        await asyncio.wait_for(
            job_queue.stop(grace_seconds=settings.shutdown_grace_seconds),
            timeout=settings.shutdown_grace_seconds,
        )
    except asyncio.TimeoutError:
        logger.warning("job queue stop timed out during shutdown")

    await engine.dispose()
    logger.info("graceful shutdown complete")
