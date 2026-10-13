import pytest
from fastapi import HTTPException

from app.services.recovery_rate_limit import (
    _enforce,
    _sliding_window,
    check_forgot_password,
    reset_memory_buckets,
)


@pytest.fixture(autouse=True)
def clear_buckets():
    reset_memory_buckets()
    yield
    reset_memory_buckets()


@pytest.mark.asyncio
async def test_forgot_password_allows_under_limit():
    await check_forgot_password("1.2.3.4", "user@example.com")


@pytest.mark.asyncio
async def test_forgot_password_blocks_ip():
    for i in range(5):
        await check_forgot_password("9.9.9.9", f"user{i}@example.com")
    with pytest.raises(HTTPException) as exc:
        await check_forgot_password("9.9.9.9", "overflow@example.com")
    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_forgot_password_blocks_per_email():
    for i in range(3):
        await check_forgot_password(f"1.2.3.{i}", "victim@example.com")
    with pytest.raises(HTTPException) as exc:
        await check_forgot_password("8.8.8.8", "victim@example.com")
    assert exc.value.status_code == 429


class _BrokenRedis:
    """Redis client that fails at command time (e.g. connection dropped mid-outage)."""

    def pipeline(self):
        class _Pipe:
            def zremrangebyscore(self, *args, **kwargs):
                pass

            def zadd(self, *args, **kwargs):
                pass

            def zcard(self, *args, **kwargs):
                pass

            def expire(self, *args, **kwargs):
                pass

            async def execute(self):
                raise ConnectionError("redis connection lost")

        return _Pipe()


@pytest.mark.asyncio
async def test_redis_outage_falls_back_to_memory_instead_of_500(monkeypatch):
    """A Redis blip during login must not surface as HTTP 500 — degrade to in-memory limits."""
    import app.services.recovery_rate_limit as rrl

    async def broken_client():
        return _BrokenRedis()

    monkeypatch.setattr(rrl, "_redis_client", broken_client)

    allowed, _ = await _sliding_window("login:ip:7.7.7.7", 2, 60)
    assert allowed is True
    allowed, _ = await _sliding_window("login:ip:7.7.7.7", 2, 60)
    assert allowed is True

    with pytest.raises(HTTPException) as exc:
        await _enforce("login:ip:7.7.7.7", 2, 60)
    assert exc.value.status_code == 429
