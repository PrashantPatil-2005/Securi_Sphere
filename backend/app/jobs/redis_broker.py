"""Redis-backed job broker."""

from __future__ import annotations

import logging

from app.jobs.queue import Job
from app.jobs.serialization import job_from_json, job_to_json

logger = logging.getLogger(__name__)

QUEUE_HIGH = "securi:jobs:high"
QUEUE_NORMAL = "securi:jobs:normal"
QUEUE_LOW = "securi:jobs:low"

PRIORITY_QUEUES = {
    0: QUEUE_HIGH,
    5: QUEUE_NORMAL,
    10: QUEUE_LOW,
}

QUEUE_ORDER = [QUEUE_HIGH, QUEUE_NORMAL, QUEUE_LOW]

_redis = None
_pool = None


async def get_redis():
    global _redis, _pool
    from app.config import settings

    if not settings.redis_url:
        return None
    if _redis is not None:
        return _redis
    try:
        from redis.asyncio import Redis

        if _pool is None:
            _pool = Redis.from_url(
                settings.redis_url,
                decode_responses=True,
                max_connections=10,
            )
        _redis = _pool
        await _redis.ping()
    except Exception as exc:
        logger.warning("Redis job broker unavailable: %s", exc)
        _redis = None
        _pool = None
    return _redis


async def close_redis() -> None:
    global _redis, _pool
    if _pool is not None:
        try:
            await _pool.aclose()
        except Exception:
            pass
    _redis = None
    _pool = None


async def redis_ping() -> bool:
    redis = await get_redis()
    if not redis:
        return False
    try:
        await redis.ping()
        return True
    except Exception:
        return False


def queue_for_priority(priority: int) -> str:
    return PRIORITY_QUEUES.get(priority, QUEUE_NORMAL)


async def enqueue_job(job: Job) -> None:
    redis = await get_redis()
    if not redis:
        raise RuntimeError("Redis job broker is not available")
    qname = queue_for_priority(job.priority)
    # Cap queue size to prevent unbounded memory growth
    queue_len = await redis.llen(qname)
    if queue_len >= 10000:
        logger.warning("job queue %s at capacity (%d) — dropping job", qname, queue_len)
        return
    await redis.lpush(qname, job_to_json(job))


async def dequeue_job(timeout: int = 5) -> Job | None:
    redis = await get_redis()
    if not redis:
        return None
    result = await redis.brpop(QUEUE_ORDER, timeout=timeout)
    if not result:
        return None
    _, payload = result
    return job_from_json(payload)


async def pending_job_count() -> int:
    redis = await get_redis()
    if not redis:
        return 0
    counts = await asyncio_gather_llen(redis)
    return sum(counts)


async def asyncio_gather_llen(redis) -> list[int]:
    import asyncio

    async def _len(key: str) -> int:
        return int(await redis.llen(key))

    return await asyncio.gather(*(_len(key) for key in QUEUE_ORDER))


DEAD_LETTER_QUEUE = "securi:jobs:dead-letter"
MAX_DEAD_LETTER_SIZE = 1000


async def enqueue_dead_letter(job: Job) -> None:
    redis = await get_redis()
    if not redis:
        return
    await redis.lpush(DEAD_LETTER_QUEUE, job_to_json(job))
    await redis.ltrim(DEAD_LETTER_QUEUE, 0, MAX_DEAD_LETTER_SIZE - 1)
