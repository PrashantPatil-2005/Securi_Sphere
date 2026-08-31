import logging
import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings
from app.core.errors import error_body
from app.core.logging import request_id_var

logger = logging.getLogger(__name__)

_redis = None


async def _redis_client():
    global _redis
    if not settings.redis_url:
        return None
    if _redis is False:
        return None
    if _redis is None:
        try:
            from redis.asyncio import Redis
            _redis = Redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=3,
                max_connections=5,
            )
            await _redis.ping()
        except Exception as exc:
            logger.warning("Redis rate limiter unavailable: %s", exc)
            _redis = None
            return None
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None and _redis is not False:
        try:
            await _redis.aclose()
        except Exception:
            pass
    _redis = None


def _client_ip(request: Request) -> str:
    if settings.trusted_proxy:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    LIMITS: dict[str, tuple[int, int]] = {
        "/api/v1/auth": (20, 60),
        "/api/v1/agent": (120, 60),
        "/api/v1/search": (30, 60),
        "/api/v1/reports": (10, 60),
        "/api/v1/analytics": (60, 60),
        "/api/v1/assistant": (15, 60),
        "/api/v1/siem": (60, 60),
    }

    def __init__(self, app):
        super().__init__(app)
        self.requests: dict[str, list[float]] = defaultdict(list)

    def _limit_for(self, path: str) -> tuple[int, int] | None:
        for prefix, limit in self.LIMITS.items():
            if path.startswith(prefix):
                return limit
        return None

    async def _check_redis(self, key: str, max_requests: int, window_seconds: int) -> bool:
        redis = await _redis_client()
        if not redis:
            return False
        pipe = redis.pipeline()
        now = int(time.time())
        window_key = f"rl:{key}"
        pipe.zremrangebyscore(window_key, 0, now - window_seconds)
        pipe.zadd(window_key, {str(now): now})
        pipe.zcard(window_key)
        pipe.expire(window_key, window_seconds)
        results = await pipe.execute()
        count = results[2]
        return count > max_requests

    async def dispatch(self, request: Request, call_next):
        if settings.testing or settings.environment == "development":
            return await call_next(request)

        limit_cfg = self._limit_for(request.url.path)
        if not limit_cfg:
            return await call_next(request)

        max_requests, window_seconds = limit_cfg
        ip = _client_ip(request)
        segment = request.url.path.split("/")[3] if len(request.url.path.split("/")) > 3 else "root"
        key = f"{ip}:{segment}"

        # Use Redis when available; fall back to in-memory only when Redis is unconfigured
        redis = await _redis_client()
        if redis:
            if await self._check_redis(key, max_requests, window_seconds):
                return self._rate_limit_response(window_seconds)
        else:
            now = time.time()
            self.requests[key] = [t for t in self.requests[key] if now - t < window_seconds]
            if len(self.requests[key]) >= max_requests:
                return self._rate_limit_response(window_seconds)
            self.requests[key].append(now)
        return await call_next(request)

    def _rate_limit_response(self, window_seconds: int) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content=error_body(
                code="rate_limit_exceeded",
                message="Rate limit exceeded",
                status_code=429,
                details={"retry_after_seconds": window_seconds},
            ),
            headers={"Retry-After": str(window_seconds), "X-Request-ID": request_id_var.get() or ""},
        )
