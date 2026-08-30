"""Application startup and shutdown lifecycle tests.

Tests startup ordering and graceful shutdown behavior.
"""
import asyncio
import pytest
from unittest.mock import patch, PropertyMock
from app.core.shutdown import ShutdownState, shutdown_state
from app.core.health import readiness
from app.jobs.queue import JobQueue

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_readiness_normal():
    result = await readiness()
    assert result["status"] in ("ready", "degraded")


@pytest.mark.asyncio
async def test_readiness_shutting_down():
    state = ShutdownState()
    state.begin()
    with patch("app.core.shutdown.shutdown_state", state):
        with patch("app.core.health.shutdown_state", state):
            result = await readiness()
            assert result["status"] == "shutting_down"


@pytest.mark.asyncio
async def test_shutdown_state_prevents_new_work():
    state = ShutdownState()
    assert state.is_shutting_down is False
    state.begin()
    assert state.is_shutting_down is True


@pytest.mark.asyncio
async def test_shutdown_state_reset():
    state = ShutdownState()
    state.begin()
    assert state.is_shutting_down is True
    state._shutting_down = False
    state._started_at = None
    state._event.clear()
    assert state.is_shutting_down is False


@pytest.mark.asyncio
async def test_job_queue_graceful_stop():
    queue = JobQueue(workers=1)
    done = asyncio.Event()

    async def slow_job(**kwargs):
        await asyncio.sleep(0.2)
        done.set()

    queue.register("slow", slow_job)
    queue.start(force=True)
    await queue.enqueue("slow", {})
    await asyncio.sleep(0.1)
    await queue.stop()
    assert done.is_set()


@pytest.mark.asyncio
async def test_job_queue_stop_cancels_pending():
    queue = JobQueue(workers=1)
    results = []

    async def blocker():
        await asyncio.sleep(5)

    async def tracker(name: str, **kwargs):
        results.append(name)

    queue.register("blocker", blocker)
    queue.register("tracker", tracker)

    queue.start(force=True)
    await queue.enqueue("blocker", {})
    await asyncio.sleep(0.1)
    await queue.enqueue("tracker", {"name": "after_stop"})
    await asyncio.sleep(0.1)
    await queue.stop()
    assert "after_stop" not in results


@pytest.mark.asyncio
async def test_scheduler_shutdown_waits():
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler()
    completed = False

    async def test_job():
        nonlocal completed
        completed = True

    scheduler.add_job(test_job, "interval", seconds=0.1)
    scheduler.start()
    # Wait long enough for at least one job execution
    await asyncio.sleep(0.3)
    scheduler.shutdown(wait=True)
    assert completed is True


@pytest.mark.asyncio
async def test_shutdown_state_event():
    state = ShutdownState()
    assert state._event.is_set() is False
    state.begin()
    assert state._event.is_set() is True


@pytest.mark.asyncio
async def test_shutdown_state_wait_started():
    state = ShutdownState()
    result = await state.wait_started(timeout=0.1)
    assert result is False
    state.begin()
    result = await state.wait_started(timeout=0.1)
    assert result is True


@pytest.mark.asyncio
async def test_shutdown_state_idempotent():
    state = ShutdownState()
    state.begin()
    first_started = state.started_at
    state.begin()
    assert state.started_at == first_started
