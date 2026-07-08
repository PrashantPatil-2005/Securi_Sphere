"""Read replica routing tests."""

import pytest

from app.database import read_replica_configured, read_session_factory, async_session


def test_read_replica_disabled_by_default():
    assert read_replica_configured() is False
    assert read_session_factory() is async_session


@pytest.mark.asyncio
async def test_read_replica_status_primary_only():
    from app.core.read_replica import read_replica_status

    status = await read_replica_status()
    assert status["enabled"] is False
    assert status["routing"] == "primary_only"


def test_database_pool_status_read_not_configured():
    from app.core.db_pool import database_pool_status

    status = database_pool_status(role="read")
    assert status["configured"] is False
    assert status["role"] == "read"


def test_database_pool_status_primary_configured():
    from app.core.db_pool import database_pool_status

    status = database_pool_status(role="primary")
    assert status["configured"] is True
    assert status["role"] == "primary"
