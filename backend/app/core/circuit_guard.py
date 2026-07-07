"""Helpers to run code behind named circuit breakers."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.config import settings
from app.core.circuit_breaker import CircuitOpenError, get_breaker

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def run_async(breaker_name: str, coro_factory: Callable[[], Awaitable[T]]) -> T:
    breaker = get_breaker(breaker_name)
    if not breaker.allow_request():
        raise CircuitOpenError(breaker_name)
    try:
        result = await coro_factory()
        breaker.record_success()
        return result
    except Exception:
        breaker.record_failure()
        raise


async def run_thread(breaker_name: str, fn: Callable[[], T], *, fallback: T | None = None) -> T | None:
    breaker = get_breaker(breaker_name)
    if not breaker.allow_request():
        logger.debug("circuit open, skipping %s", breaker_name)
        return fallback
    try:
        result = await asyncio.to_thread(fn)
        breaker.record_success()
        return result
    except Exception:
        breaker.record_failure()
        raise
