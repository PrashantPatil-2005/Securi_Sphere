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


async def get_redis():
    global _redis
    from app.config import settings

    if not settings.redis_url:
        return None
    if _redis is None:
        try:
            from redis.asyncio import Redis

            _redis = Redis.from_url(settings.redis_url, decode_responses=True)
            await _redis.ping()
        except Exception as exc:
            logger.warning("Redis job broker unavailable: %s", exc)
            _redis = False
    return _redis if _redis is not False else None


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
    await redis.lpush(queue_for_priority(job.priority), job_to_json(job))


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
