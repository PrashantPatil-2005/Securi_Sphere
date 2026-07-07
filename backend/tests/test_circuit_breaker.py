"""Circuit breaker unit tests."""

import time

import pytest

from app.core.circuit_breaker import CircuitBreaker, CircuitOpenError, get_breaker
from app.core.circuit_guard import run_async


def test_breaker_opens_after_threshold(monkeypatch):
    monkeypatch.setattr("app.core.circuit_breaker.settings.circuit_breakers_enabled", True)
    breaker = CircuitBreaker("unit", failure_threshold=3, recovery_seconds=60)

    for _ in range(3):
        breaker.record_failure()

    assert breaker.is_open()
    assert breaker.state == "open"


def test_breaker_half_open_after_recovery(monkeypatch):
    monkeypatch.setattr("app.core.circuit_breaker.settings.circuit_breakers_enabled", True)
    breaker = CircuitBreaker("half", failure_threshold=2, recovery_seconds=0.01)

    breaker.record_failure()
    breaker.record_failure()
    assert breaker.is_open()

    time.sleep(0.02)
    assert breaker.state == "half_open"
    assert breaker.allow_request() is True


def test_breaker_success_closes_from_half_open(monkeypatch):
    monkeypatch.setattr("app.core.circuit_breaker.settings.circuit_breakers_enabled", True)
    breaker = CircuitBreaker("close", failure_threshold=2, recovery_seconds=0.01)

    breaker.record_failure()
    breaker.record_failure()
    time.sleep(0.02)
    assert breaker.state == "half_open"

    breaker.record_success()
    assert breaker.state == "closed"
    assert breaker._failures == 0


@pytest.mark.asyncio
async def test_run_async_opens_on_failures(monkeypatch):
    monkeypatch.setattr("app.core.circuit_breaker.settings.circuit_breakers_enabled", True)
    monkeypatch.setattr("app.core.circuit_breaker.settings.circuit_breaker_failure_threshold", 3)
    breaker = get_breaker("test_async_fail")
    breaker.record_success()

    async def fail():
        raise RuntimeError("down")

    for _ in range(3):
        with pytest.raises(RuntimeError):
            await run_async("test_async_fail", fail)

    assert breaker.is_open()

    with pytest.raises(CircuitOpenError):
        await run_async("test_async_fail", fail)


@pytest.mark.asyncio
async def test_run_async_success_resets_failures(monkeypatch):
    monkeypatch.setattr("app.core.circuit_breaker.settings.circuit_breakers_enabled", True)
    breaker = get_breaker("test_async_ok")
    breaker.record_failure()
    breaker.record_failure()

    async def ok():
        return "ok"

    result = await run_async("test_async_ok", ok)
    assert result == "ok"
    assert breaker.state == "closed"


@pytest.mark.asyncio
async def test_run_async_bypass_when_disabled(monkeypatch):
    monkeypatch.setattr("app.core.circuit_breaker.settings.circuit_breakers_enabled", False)
    breaker = get_breaker("test_disabled")
    for _ in range(10):
        breaker.record_failure()
    assert breaker.is_open()

    async def ok():
        return 42

    assert await run_async("test_disabled", ok) == 42
