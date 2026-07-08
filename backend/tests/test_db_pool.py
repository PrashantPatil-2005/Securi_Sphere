"""Database connection pool configuration tests."""

from app.config import settings
from app.core.db_pool import database_pool_status, engine_options, estimate_cluster_connections
from app.database import engine


def test_engine_options_match_settings():
    opts = engine_options()
    assert opts["pool_size"] == settings.db_pool_size
    assert opts["max_overflow"] == settings.db_max_overflow
    assert opts["pool_timeout"] == settings.db_pool_timeout
    assert opts["pool_recycle"] == settings.db_pool_recycle
    assert opts["pool_pre_ping"] is settings.db_pool_pre_ping


def test_engine_uses_queue_pool():
    assert engine.pool.__class__.__name__ in ("AsyncAdaptedQueuePool", "QueuePool")


def test_database_pool_status_shape():
    status = database_pool_status()
    assert status["configured"] is True
    assert status["role"] == "primary"
    assert status["pool_size"] == settings.db_pool_size
    assert status["capacity"] == settings.db_pool_size + settings.db_max_overflow
    assert "utilization" in status
    assert status["checked_out"] >= 0


def test_cluster_connection_estimate():
    estimate = estimate_cluster_connections(api_replicas=3, worker_replicas=2)
    per = settings.db_pool_size + settings.db_max_overflow
    assert estimate["per_process_max"] == per
    assert estimate["process_count"] == 5
    assert estimate["cluster_max"] == per * 5
