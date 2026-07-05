"""Unit tests for job queue serialization and memory backend."""

import pytest

from app.jobs.queue import Job, JobPriority, JobQueue
from app.jobs.serialization import job_from_json, job_to_json


def test_job_json_roundtrip():
    job = Job(priority=5, name="notify_alert", payload={"alert_id": "abc-123"}, id="job-1")
    restored = job_from_json(job_to_json(job))
    assert restored.id == job.id
    assert restored.name == job.name
    assert restored.payload == job.payload
    assert restored.priority == job.priority


@pytest.mark.asyncio
async def test_memory_queue_enqueue_and_run():
    queue = JobQueue(workers=1)
    seen: list[str] = []

    async def handler(alert_id: str) -> None:
        seen.append(alert_id)

    queue.register("notify_alert", handler)
    queue.start(force=True)
    await queue.enqueue("notify_alert", {"alert_id": "x"}, priority=JobPriority.HIGH)

    for _ in range(20):
        if seen:
            break
        await asyncio_sleep(0.05)

    await queue.stop()
    assert seen == ["x"]


async def asyncio_sleep(seconds: float) -> None:
    import asyncio

    await asyncio.sleep(seconds)
