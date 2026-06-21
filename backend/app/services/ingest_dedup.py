"""Event ingest deduplication — Redis when available, Postgres fallback."""

import hashlib
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = logging.getLogger(__name__)

_redis_client = None


def event_fingerprint(host_id, timestamp: datetime, event_type: str, raw_log: str | None) -> str:
    raw = f"{host_id}:{timestamp.isoformat()}:{event_type}:{raw_log or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def _get_redis():
    global _redis_client
    if not settings.redis_url:
        return None
    if _redis_client is None:
        try:
            from redis.asyncio import Redis
            _redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
            await _redis_client.ping()
        except Exception as exc:
            logger.warning("Redis unavailable for dedup: %s", exc)
            _redis_client = False
    return _redis_client if _redis_client is not False else None


async def is_duplicate(db: AsyncSession, fingerprint: str) -> bool:
    redis = await _get_redis()
    if redis:
        key = f"dedup:{fingerprint}"
        if await redis.exists(key):
            return True
        await redis.setex(key, settings.idempotency_ttl_seconds, "1")
        return False

    from app.models.ingest_dedup import IngestDedup

    cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.idempotency_ttl_seconds)
    await db.execute(delete(IngestDedup).where(IngestDedup.created_at < cutoff))

    existing = (
        await db.execute(select(IngestDedup).where(IngestDedup.fingerprint == fingerprint))
    ).scalar_one_or_none()
    if existing:
        return True

    db.add(IngestDedup(fingerprint=fingerprint))
    return False
