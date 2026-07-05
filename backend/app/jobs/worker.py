"""Dedicated Redis job worker process."""

from __future__ import annotations

import asyncio
import logging
import signal

from app.config import settings
from app.core.logging import configure_logging
from app.jobs.handlers import register_job_handlers
from app.jobs.queue import job_queue
from app.services.migrate import migrate_schema

logger = logging.getLogger(__name__)


async def run_worker() -> None:
    configure_logging()

    if settings.job_queue_backend != "redis" or not settings.redis_url:
        raise SystemExit("Worker requires JOB_QUEUE_BACKEND=redis and REDIS_URL")

    await migrate_schema()
    register_job_handlers()
    job_queue.start(force=True)

    stop_event = asyncio.Event()

    def _stop(*_args) -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _stop)
        except NotImplementedError:
            signal.signal(sig, lambda *_: _stop())

    logger.info("job worker running", extra={"workers": settings.job_queue_workers})
    await stop_event.wait()
    await job_queue.stop()
    logger.info("job worker stopped")


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
