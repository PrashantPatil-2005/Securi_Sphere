"""Dedicated rate limits for account recovery and MFA verification."""

from __future__ import annotations

import logging
import time
from collections import defaultdict

from fastapi import HTTPException

from app.config import settings

logger = logging.getLogger(__name__)

_redis = None
_memory: dict[str, list[float]] = defaultdict(list)


async def _redis_client():
    global _redis
    if not settings.redis_url:
        return None
    if _redis is None:
        try:
            from redis.asyncio import Redis

            _redis = Redis.from_url(settings.redis_url, decode_responses=True)
            await _redis.ping()
        except Exception as exc:
            logger.warning("Redis recovery rate limiter unavailable: %s", exc)
            _redis = False
    return _redis if _redis is not False else None


async def _sliding_window(key: str, max_requests: int, window_seconds: int) -> tuple[bool, int]:
    redis = await _redis_client()
    if redis:
        now = int(time.time())
        window_key = f"recovery:{key}"
        pipe = redis.pipeline()
        pipe.zremrangebyscore(window_key, 0, now - window_seconds)
        pipe.zadd(window_key, {f"{now}:{time.time_ns()}": now})
        pipe.zcard(window_key)
        pipe.expire(window_key, window_seconds)
        results = await pipe.execute()
        count = results[2]
        if count > max_requests:
            return False, window_seconds
        return True, 0

    now = time.time()
    bucket = _memory[key]
    _memory[key] = [t for t in bucket if now - t < window_seconds]
    if len(_memory[key]) >= max_requests:
        oldest = _memory[key][0] if _memory[key] else now
        retry = max(1, int(window_seconds - (now - oldest)))
        return False, retry
    _memory[key].append(now)
    return True, 0


def _raise_rate_limited(retry_after: int) -> None:
    raise HTTPException(
        status_code=429,
        detail="Too many recovery attempts. Please try again later.",
        headers={"Retry-After": str(retry_after)},
    )


async def _enforce(key: str, max_requests: int, window_seconds: int) -> None:
    allowed, retry_after = await _sliding_window(key, max_requests, window_seconds)
    if not allowed:
        _raise_rate_limited(retry_after)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


async def check_forgot_password(ip: str, email: str) -> None:
    await _enforce(
        f"forgot:ip:{ip}",
        settings.recovery_forgot_ip_limit,
        settings.recovery_forgot_ip_window_seconds,
    )
    await _enforce(
        f"forgot:email:{_normalize_email(email)}",
        settings.recovery_forgot_email_limit,
        settings.recovery_forgot_email_window_seconds,
    )


async def check_reset_password(ip: str) -> None:
    await _enforce(
        f"reset:ip:{ip}",
        settings.recovery_reset_ip_limit,
        settings.recovery_reset_ip_window_seconds,
    )


async def record_reset_token_failure(token: str) -> None:
    from app.security import hash_token

    key = f"reset:token:{hash_token(token)[:16]}"
    await _enforce(
        key,
        settings.recovery_reset_token_fail_limit,
        settings.recovery_reset_token_fail_window_seconds,
    )


async def check_mfa_verify(ip: str) -> None:
    await _enforce(
        f"mfa:ip:{ip}",
        settings.recovery_mfa_ip_limit,
        settings.recovery_mfa_ip_window_seconds,
    )


def reset_memory_buckets() -> None:
    """Test helper."""
    _memory.clear()
