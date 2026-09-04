"""Real Redis integration tests.

These tests FAIL if Redis is not available (not skipped).
"""
import asyncio
import pytest
from redis.asyncio import Redis

pytestmark = [pytest.mark.integration, pytest.mark.redis]


@pytest.mark.asyncio
async def test_redis_connection_works(require_redis):
    result = await require_redis.ping()
    assert result is True


@pytest.mark.asyncio
async def test_redis_set_get(require_redis):
    await require_redis.set("test_key", "test_value", ex=10)
    value = await require_redis.get("test_key")
    assert value == "test_value"
    await require_redis.delete("test_key")


@pytest.mark.asyncio
async def test_redis_connection_pool(require_redis):
    for i in range(10):
        await require_redis.set(f"pool_test_{i}", str(i), ex=10)
    for i in range(10):
        value = await require_redis.get(f"pool_test_{i}")
        assert value == str(i)
    for i in range(10):
        await require_redis.delete(f"pool_test_{i}")


@pytest.mark.asyncio
async def test_redis_close_and_reopen(require_redis):
    from app.config import settings
    new_conn = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        result = await new_conn.ping()
        assert result is True
    finally:
        await new_conn.aclose()


@pytest.mark.asyncio
async def test_redis_pubsub_publish_receive(require_redis):
    received = []

    async def subscriber():
        pubsub = require_redis.pubsub()
        await pubsub.subscribe("test_channel")
        try:
            async for message in pubsub.listen():
                if message.get("type") == "message":
                    received.append(message["data"])
                    break
        finally:
            await pubsub.unsubscribe("test_channel")
            await pubsub.close()

    async def publisher():
        await asyncio.sleep(0.2)
        await require_redis.publish("test_channel", "hello")

    await asyncio.gather(subscriber(), publisher())
    assert received == ["hello"]


@pytest.mark.asyncio
async def test_redis_failure_detection(require_redis):
    bad_conn = Redis.from_url("redis://localhost:19999", decode_responses=True, socket_timeout=2)
    try:
        with pytest.raises(Exception):
            await bad_conn.ping()
    finally:
        await bad_conn.aclose()


@pytest.mark.asyncio
async def test_redis_recovery_after_restart(require_redis):
    from app.config import settings
    conn = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        result = await conn.ping()
        assert result is True
        await conn.set("recovery_test", "ok", ex=10)
        val = await conn.get("recovery_test")
        assert val == "ok"
        await conn.delete("recovery_test")
    finally:
        await conn.aclose()


@pytest.mark.asyncio
async def test_redis_job_enqueue_dequeue(require_redis):
    from app.jobs.redis_broker import enqueue_job, dequeue_job
    from app.jobs.queue import Job

    job = Job(priority=5, name="test_handler", payload={"key": "value"})
    await enqueue_job(job)
    dequeued = await dequeue_job(timeout=2)
    assert dequeued is not None
    assert dequeued.name == "test_handler"
    assert dequeued.payload == {"key": "value"}


@pytest.mark.asyncio
async def test_redis_job_priority_order(require_redis):
    from app.jobs.redis_broker import enqueue_job, dequeue_job
    from app.jobs.queue import Job

    low = Job(priority=10, name="low_job", payload={})
    normal = Job(priority=5, name="normal_job", payload={})
    high = Job(priority=0, name="high_job", payload={})

    await enqueue_job(low)
    await enqueue_job(normal)
    await enqueue_job(high)

    first = await dequeue_job(timeout=2)
    assert first is not None
    assert first.name == "high_job"

    second = await dequeue_job(timeout=2)
    assert second is not None
    assert second.name == "normal_job"

    third = await dequeue_job(timeout=2)
    assert third is not None
    assert third.name == "low_job"
