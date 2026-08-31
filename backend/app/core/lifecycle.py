"""Graceful shutdown orchestration."""

from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.core.shutdown import shutdown_state
from app.database import dispose_engines
from app.jobs.queue import JobQueue
from app.websocket.manager import ConnectionManager

logger = logging.getLogger(__name__)


async def shutdown_application(
    *,
    scheduler: AsyncIOScheduler,
    job_queue: JobQueue,
    ws_manager: ConnectionManager,
) -> None:
    """Drain work and release resources within the configured grace window.

    Shutdown order:
    1. Signal shutdown state (health probes return 503)
    2. Stop scheduler (no new scheduled jobs)
    3. Stop job queue (wait for active jobs with timeout)
    4. Stop WebSocket manager (close connections, cancel Redis listener)
    5. Close database connections
    """
    shutdown_state.begin()
    grace = settings.shutdown_grace_seconds
    logger.info("graceful shutdown started", extra={"grace_seconds": grace})

    if scheduler.running:
        try:
            scheduler.shutdown(wait=True)
        except Exception:
            logger.warning("scheduler shutdown raised exception", exc_info=True)

    try:
        await asyncio.wait_for(
            job_queue.stop(grace_seconds=grace),
            timeout=grace + 2,
        )
    except asyncio.TimeoutError:
        logger.warning("job queue stop timed out during shutdown")

    try:
        await asyncio.wait_for(ws_manager.stop(), timeout=5)
    except asyncio.TimeoutError:
        logger.warning("websocket manager stop timed out")

    from app.websocket.redis_pubsub import close_redis as close_ws_redis
    from app.jobs.redis_broker import close_redis as close_broker_redis
    from app.middleware.rate_limit import close_redis as close_rl_redis
    from app.services.recovery_rate_limit import close_redis as close_recovery_redis
    from app.services.ingest_dedup import close_redis as close_dedup_redis
    try:
        await asyncio.wait_for(
            asyncio.gather(
                close_ws_redis(),
                close_broker_redis(),
                close_rl_redis(),
                close_recovery_redis(),
                close_dedup_redis(),
            ),
            timeout=5,
        )
    except asyncio.TimeoutError:
        logger.warning("redis cleanup timed out")

    try:
        await asyncio.wait_for(dispose_engines(), timeout=5)
    except asyncio.TimeoutError:
        logger.warning("database dispose timed out")

    logger.info("graceful shutdown complete")
