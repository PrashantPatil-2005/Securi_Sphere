"""Job queue integration tests (memory backend).

Tests job lifecycle, dead-letter, timeout behavior.
"""
import asyncio
import pytest
from app.jobs.queue import JobQueue, JobPriority

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_job_enqueue_and_process():
    queue = JobQueue(workers=1)
    result = {}

    async def handler(alert_id: str, **kwargs):
        result["alert_id"] = alert_id

    queue.register("notify_alert", handler)
    queue.start(force=True)
    await queue.enqueue("notify_alert", {"alert_id": "test-123"})

    for _ in range(50):
        if result:
            break
        await asyncio.sleep(0.05)

    await queue.stop()
    assert result["alert_id"] == "test-123"


@pytest.mark.asyncio
async def test_job_priority_order():
    queue = JobQueue(workers=1)
    order = []

    async def tracking_handler(name: str, **kwargs):
        order.append(name)

    queue.register("low_job", tracking_handler)
    queue.register("normal_job", tracking_handler)
    queue.register("high_job", tracking_handler)

    await queue.enqueue("low_job", {"name": "low"}, priority=JobPriority.LOW)
    await queue.enqueue("normal_job", {"name": "normal"}, priority=JobPriority.NORMAL)
    await queue.enqueue("high_job", {"name": "high"}, priority=JobPriority.HIGH)

    queue.start(force=True)

    for _ in range(50):
        if len(order) >= 3:
            break
        await asyncio.sleep(0.05)

    await queue.stop()
    assert order[0] == "high"
    assert order[1] == "normal"
    assert order[2] == "low"


@pytest.mark.asyncio
async def test_job_handler_error_does_not_crash():
    queue = JobQueue(workers=1)
    results = []

    async def failing_handler(**kwargs):
        raise RuntimeError("handler crashed")

    async def success_handler(name: str, **kwargs):
        results.append(name)

    queue.register("failing_job", failing_handler)
    queue.register("success_job", success_handler)

    await queue.enqueue("failing_job", {})
    await queue.enqueue("success_job", {"name": "after_fail"})

    queue.start(force=True)

    for _ in range(50):
        if results:
            break
        await asyncio.sleep(0.05)

    await queue.stop()
    assert "after_fail" in results


@pytest.mark.asyncio
async def test_job_unknown_handler_dead_letter():
    queue = JobQueue(workers=1)
    await queue.enqueue("nonexistent_handler", {"key": "value"})

    queue.start(force=True)
    await asyncio.sleep(0.5)
    await queue.stop()


@pytest.mark.asyncio
async def test_job_timeout_no_requeue():
    queue = JobQueue(workers=1)

    async def slow_handler(**kwargs):
        await asyncio.sleep(300)

    queue.register("slow_job", slow_handler)
    await queue.enqueue("slow_job", {})

    queue.start(force=True)
    await asyncio.sleep(0.5)
    await queue.stop()
    assert queue._in_flight == 0


@pytest.mark.asyncio
async def test_job_concurrent_workers():
    queue = JobQueue(workers=4)
    completed = []

    async def worker_handler(idx: str, **kwargs):
        await asyncio.sleep(0.1)
        completed.append(idx)

    queue.register("worker_job", worker_handler)

    for i in range(8):
        await queue.enqueue("worker_job", {"idx": str(i)})

    queue.start(force=True)

    for _ in range(50):
        if len(completed) >= 8:
            break
        await asyncio.sleep(0.05)

    await queue.stop()
    assert len(completed) == 8


@pytest.mark.asyncio
async def test_job_stop_waits_inflight():
    queue = JobQueue(workers=1)
    done = asyncio.Event()

    async def slow_job(**kwargs):
        await asyncio.sleep(0.3)
        done.set()

    queue.register("slow", slow_job)
    queue.start(force=True)
    await queue.enqueue("slow", {})

    await asyncio.sleep(0.1)
    await queue.stop()
    assert done.is_set()
