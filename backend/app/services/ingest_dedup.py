"""Event ingest deduplication — Redis when available, Postgres fallback."""

import hashlib
import logging
from datetime import datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert
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
            _redis_client = Redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=3,
                max_connections=5,
            )
            await _redis_client.ping()
        except Exception as exc:
            logger.warning("Redis unavailable for dedup: %s", exc)
            _redis_client = None
    return _redis_client if _redis_client is not None else None


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.aclose()
        except Exception:
            pass
    _redis_client = None


async def is_duplicate(db: AsyncSession, fingerprint: str) -> bool:
    redis = await _get_redis()
    if redis:
        key = f"dedup:{fingerprint}"
        added = await redis.set(key, "1", nx=True, ex=settings.idempotency_ttl_seconds)
        return added is None

    from app.models.ingest_dedup import IngestDedup

    stmt = (
        pg_insert(IngestDedup)
        .values(fingerprint=fingerprint)
        .on_conflict_do_nothing(index_elements=["fingerprint"])
    )
    result = await db.execute(stmt)
    return result.rowcount == 0
