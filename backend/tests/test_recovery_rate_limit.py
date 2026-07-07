import pytest
from fastapi import HTTPException

from app.services.recovery_rate_limit import (
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
