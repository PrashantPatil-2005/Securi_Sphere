"""Graceful shutdown behavior."""

import pytest

from app.core.shutdown import shutdown_state
from app.core.health import readiness
from app.jobs.queue import JobQueue


@pytest.mark.asyncio
async def test_readiness_shutting_down_returns_503_status():
    shutdown_state.begin()
    try:
        body = await readiness()
        assert body["status"] == "shutting_down"
    finally:
        shutdown_state._shutting_down = False
        shutdown_state._started_at = None
        shutdown_state._event.clear()


@pytest.mark.asyncio
async def test_job_queue_waits_for_in_flight():
    queue = JobQueue(workers=1)
    started = False
    finished = False

    async def slow_job() -> None:
        nonlocal started, finished
        started = True
        import asyncio

        await asyncio.sleep(0.2)
        finished = True

    queue.register("slow", slow_job)
    queue.start(force=True)
    await queue.enqueue("slow")
    await __import__("asyncio").sleep(0.05)
    await queue.stop(grace_seconds=1.0)
    assert started is True
    assert finished is True
