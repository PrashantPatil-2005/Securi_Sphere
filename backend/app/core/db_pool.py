"""SQLAlchemy connection pool configuration and observability."""

from __future__ import annotations

from typing import Any

from app.config import settings


def engine_options() -> dict[str, Any]:
    return {
        "pool_size": settings.db_pool_size,
        "max_overflow": settings.db_max_overflow,
        "pool_timeout": settings.db_pool_timeout,
        "pool_recycle": settings.db_pool_recycle,
        "pool_pre_ping": settings.db_pool_pre_ping,
    }


def database_pool_status() -> dict[str, Any]:
    from app.database import engine

    pool = engine.pool
    capacity = settings.db_pool_size + settings.db_max_overflow
    checked_out = pool.checkedout()
    return {
        "pool_size": settings.db_pool_size,
        "max_overflow": settings.db_max_overflow,
        "pool_timeout_seconds": settings.db_pool_timeout,
        "pool_recycle_seconds": settings.db_pool_recycle,
        "pool_pre_ping": settings.db_pool_pre_ping,
        "checked_out": checked_out,
        "checked_in": pool.checkedin(),
        "overflow": pool.overflow(),
        "capacity": capacity,
        "utilization": round(checked_out / capacity, 3) if capacity else 0.0,
    }


def estimate_cluster_connections(*, api_replicas: int, worker_replicas: int = 0) -> dict[str, int]:
    """Rough max Postgres connections if every pool slot is in use."""
    per_process = settings.db_pool_size + settings.db_max_overflow
    processes = max(0, api_replicas) + max(0, worker_replicas)
    return {
        "per_process_max": per_process,
        "process_count": processes,
        "cluster_max": per_process * processes,
    }
