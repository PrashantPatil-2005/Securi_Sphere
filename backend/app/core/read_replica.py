"""PostgreSQL read replica routing and health."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.config import settings
from app.database import read_replica_configured, read_session_factory


async def read_replica_status() -> dict[str, Any]:
    if not read_replica_configured():
        return {"enabled": False, "routing": "primary_only"}

    try:
        async with read_session_factory()() as db:
            await db.execute(text("SELECT 1"))
            lag_result = await db.execute(
                text(
                    "SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp()))::float"
                )
            )
            lag_seconds = lag_result.scalar()
    except Exception as exc:
        return {"enabled": True, "healthy": False, "error": str(exc)}

    lag_warn = lag_seconds is not None and lag_seconds > settings.read_replica_lag_warn_seconds
    return {
        "enabled": True,
        "healthy": True,
        "lag_seconds": lag_seconds,
        "lag_warn": lag_warn,
        "lag_warn_threshold_seconds": settings.read_replica_lag_warn_seconds,
    }
