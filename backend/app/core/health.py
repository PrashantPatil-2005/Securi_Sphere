from datetime import datetime, timezone

from sqlalchemy import text

from app.database import async_session
from app.config import settings
from app.core.circuit_breaker import get_breaker
from app.core.shutdown import shutdown_state
from app.jobs.queue import job_queue
from app.jobs.redis_broker import redis_ping
from app.websocket.manager import ws_manager
from app.websocket.redis_pubsub import ws_pubsub_ping


async def liveness() -> dict:
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}


async def startup() -> dict:
    """Startup probe — database only (migrations may still be running on first boot)."""
    checks: dict[str, str] = {}
    try:
        async with async_session() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"

    started = checks.get("database") == "ok"
    return {
        "status": "started" if started else "starting",
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def readiness() -> dict:
    if shutdown_state.is_shutting_down:
        return {
            "status": "shutting_down",
            "checks": {"shutdown": "in_progress"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    checks: dict[str, str] = {}
    try:
        async with async_session() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"

    checks["job_queue"] = "ok" if job_queue.is_running else "stopped"
    if settings.job_queue_backend == "redis" and settings.redis_url:
        checks["job_broker"] = "ok" if await redis_ping() else "error"
        if not settings.job_queue_run_workers:
            checks["job_queue"] = checks["job_broker"]
    if settings.ws_pubsub_backend == "redis" and settings.redis_url:
        checks["ws_pubsub"] = "ok" if await ws_pubsub_ping() else "error"
    if settings.opensearch_url and settings.search_backend == "opensearch":
        breaker = get_breaker("opensearch")
        if settings.circuit_breakers_enabled and breaker.is_open():
            checks["opensearch"] = "circuit_open"
        else:
            from app.search.opensearch_client import opensearch_cluster_health

            os_health = await opensearch_cluster_health()
            checks["opensearch"] = os_health.get("status", "unknown") if os_health else "error"

    if settings.read_replica_enabled:
        from app.core.read_replica import read_replica_status

        replica = await read_replica_status()
        if replica.get("healthy"):
            checks["read_replica"] = "ok"
            if replica.get("lag_warn"):
                checks["read_replica_lag"] = f"warn:{replica.get('lag_seconds')}s"
        else:
            checks["read_replica"] = replica.get("error", "error")

    ready = checks["database"] == "ok" and (
        checks.get("job_broker") == "ok"
        or checks.get("ws_pubsub") == "ok"
        or checks["job_queue"] == "ok"
    )
    return {
        "status": "ready" if ready else "degraded",
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
