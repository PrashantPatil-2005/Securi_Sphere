"""Composite component health for the operational dashboard.

Each component reports one of four states — healthy, degraded, unavailable,
unknown — plus a safe diagnostic message, impaired functionality, a next
action, and a last-checked timestamp. Messages never include connection
strings, credentials, tokens, or raw exception traces.

A successful Redis ping is deliberately NOT treated as proof that the job
queue is healthy: the queue component separately checks broker reachability,
worker heartbeat freshness, and backlog.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import text

from app.config import settings
from app.core.circuit_breaker import get_breaker
from app.jobs.queue import job_queue
from app.websocket.manager import ws_manager

logger = logging.getLogger(__name__)

HEALTHY = "healthy"
DEGRADED = "degraded"
UNAVAILABLE = "unavailable"
UNKNOWN = "unknown"

WORKER_HEARTBEAT_FRESH_SECONDS = 60
QUEUE_BACKLOG_DEGRADED = 100
QUEUE_BACKLOG_UNAVAILABLE = 5000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _component(
    component_id: str,
    name: str,
    status: str,
    message: str,
    *,
    impaired: list[str] | None = None,
    next_action: str | None = None,
    detail: dict | None = None,
) -> dict:
    return {
        "id": component_id,
        "name": name,
        "status": status,
        "message": message,
        "impaired": impaired or [],
        "next_action": next_action,
        "last_checked": _now(),
        "detail": detail or {},
    }


async def _check_postgres() -> dict:
    from app.database import async_session

    try:
        async with async_session() as db:
            await db.execute(text("SELECT 1"))
        return _component(
            "postgres",
            "PostgreSQL",
            HEALTHY,
            "Primary database is reachable and responding to queries.",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("postgres health check failed: %s", type(exc).__name__)
        return _component(
            "postgres",
            "PostgreSQL",
            UNAVAILABLE,
            "Primary database is not reachable. Events, alerts, hosts, and cases cannot be read or written.",
            impaired=["event ingestion", "alerting", "case workspace", "host inventory"],
            next_action="Check that the securi-postgres container is running and accepts connections, then retry.",
        )


async def _check_redis() -> dict:
    if not settings.redis_url:
        return _component(
            "redis",
            "Redis",
            UNKNOWN,
            "Redis is not configured. In-memory fallbacks are used for pub/sub and (if enabled) the job queue.",
            next_action="Set REDIS_URL to enable shared pub/sub and the Redis job broker.",
        )
    from app.jobs.redis_broker import redis_ping

    try:
        ok = await redis_ping()
    except Exception:  # noqa: BLE001
        ok = False
    if ok:
        return _component(
            "redis",
            "Redis",
            HEALTHY,
            "Redis responded to a ping.",
            detail={"configured": True},
        )
    return _component(
        "redis",
        "Redis",
        UNAVAILABLE,
        "Redis is configured but did not respond to a ping. Cross-instance broadcasts and the Redis job broker are impaired.",
        impaired=["live updates across instances", "Redis job broker"],
        next_action="Check that the securi-redis container is running and REDIS_URL points at it, then retry.",
        detail={"configured": True},
    )


async def _check_job_queue(redis_ok: bool | None) -> dict:
    """Job queue health — intentionally independent of the Redis ping result."""
    pending: int | None = None
    try:
        pending = await job_queue.pending_count()
    except Exception:  # noqa: BLE001
        pending = None

    detail = {
        "backend": job_queue.backend_name,
        "pending": pending,
        "run_workers_in_this_process": job_queue.is_running,
    }

    if job_queue.backend_name == "redis":
        if redis_ok is False:
            return _component(
                "job_queue",
                "Job queue",
                UNAVAILABLE,
                "The Redis job broker is unreachable, so enqueued jobs cannot be delivered to workers.",
                impaired=["detection re-scoring jobs", "playbook dispatch", "scheduled analytics"],
                next_action="Restore Redis connectivity, then retry — queued jobs will resume once the broker is reachable.",
                detail=detail,
            )
        if redis_ok is None:
            return _component(
                "job_queue",
                "Job queue",
                UNKNOWN,
                "Broker reachability could not be determined, so job processing state is unknown.",
                next_action="Verify Redis connectivity, then retry.",
                detail=detail,
            )

        from app.jobs.redis_broker import worker_heartbeat_age_seconds

        age = await worker_heartbeat_age_seconds()
        detail["worker_heartbeat_age_seconds"] = age
        if age is None:
            return _component(
                "job_queue",
                "Job queue",
                DEGRADED,
                "The Redis broker is reachable, but no worker heartbeat has been observed — jobs may be enqueued without being processed.",
                impaired=["async job processing (detection re-score, playbooks)"],
                next_action="Confirm the securi-worker container is running, then retry.",
                detail=detail,
            )
        if age > WORKER_HEARTBEAT_FRESH_SECONDS:
            return _component(
                "job_queue",
                "Job queue",
                UNAVAILABLE,
                f"No worker heartbeat for {int(age)}s — the broker is reachable but no worker is processing jobs.",
                impaired=["async job processing (detection re-score, playbooks)"],
                next_action="Restart the securi-worker container, then retry.",
                detail=detail,
            )
        if pending is not None and pending >= QUEUE_BACKLOG_UNAVAILABLE:
            return _component(
                "job_queue",
                "Job queue",
                UNAVAILABLE,
                f"Worker is alive but the backlog is {pending} jobs — processing has effectively stopped.",
                impaired=["async job processing (detection re-score, playbooks)"],
                next_action="Inspect worker logs for failing job handlers, then restart the worker.",
                detail=detail,
            )
        if pending is not None and pending >= QUEUE_BACKLOG_DEGRADED:
            return _component(
                "job_queue",
                "Job queue",
                DEGRADED,
                f"Worker is alive but the backlog is {pending} jobs — processing is slower than intake.",
                next_action="Monitor the backlog; investigate worker latency if it keeps growing.",
                detail=detail,
            )
        return _component(
            "job_queue",
            "Job queue",
            HEALTHY,
            f"Redis broker reachable, worker heartbeat fresh ({int(age)}s ago), backlog {pending if pending is not None else 'n/a'}.",
            detail=detail,
        )

    # Memory backend
    if job_queue.is_running:
        return _component(
            "job_queue",
            "Job queue",
            HEALTHY,
            "In-memory queue with in-process workers running.",
            detail=detail,
        )
    if not settings.job_queue_run_workers:
        return _component(
            "job_queue",
            "Job queue",
            UNAVAILABLE,
            "In-memory queue with workers disabled in this process — enqueued jobs are never processed.",
            impaired=["async job processing (detection re-score, playbooks)"],
            next_action="Enable JOB_QUEUE_RUN_WORKERS or configure the Redis broker with the securi-worker container.",
            detail=detail,
        )
    return _component(
        "job_queue",
        "Job queue",
        DEGRADED,
        "In-memory queue workers are not running in this process.",
        impaired=["async job processing (detection re-score, playbooks)"],
        next_action="Restart the API process so job workers start, or switch to the Redis broker.",
        detail=detail,
    )


async def _check_search() -> dict:
    if not (settings.opensearch_url and settings.search_backend == "opensearch"):
        return _component(
            "search",
            "Search",
            HEALTHY,
            "PostgreSQL-backed search is in use (OpenSearch not configured).",
            detail={"backend": "postgres"},
        )

    breaker = get_breaker("opensearch")
    if settings.circuit_breakers_enabled and breaker.is_open():
        return _component(
            "search",
            "Search",
            DEGRADED,
            "The OpenSearch circuit breaker is open after repeated failures; search requests are being short-circuited.",
            impaired=["global search", "SIEM search", "search-backed analytics"],
            next_action="Verify the securi-opensearch container, then wait for the breaker to half-open or retry after recovery.",
            detail={"backend": "opensearch", "circuit": "open"},
        )

    from app.search.opensearch_client import opensearch_cluster_health

    try:
        os_health = await opensearch_cluster_health()
    except Exception:  # noqa: BLE001
        os_health = None
    if not os_health:
        return _component(
            "search",
            "Search",
            UNAVAILABLE,
            "OpenSearch is configured but cluster health could not be retrieved.",
            impaired=["global search", "SIEM search"],
            next_action="Check the securi-opensearch container and OPENSEARCH_URL, then retry.",
            detail={"backend": "opensearch"},
        )
    cluster = os_health.get("status", "unknown")
    nodes = os_health.get("number_of_nodes")
    detail = {"backend": "opensearch", "cluster_status": cluster}
    if nodes is not None:
        detail["nodes"] = nodes
    if cluster == "green":
        return _component("search", "Search", HEALTHY, "OpenSearch cluster status is green.", detail=detail)
    if cluster == "yellow":
        return _component(
            "search",
            "Search",
            DEGRADED,
            "OpenSearch cluster status is yellow (replicas unassigned) — search works but redundancy is reduced.",
            impaired=[],
            next_action="Check disk space and shard allocation on the OpenSearch node.",
            detail=detail,
        )
    return _component(
        "search",
        "Search",
        UNAVAILABLE,
        f"OpenSearch cluster status is '{cluster}' — search results may be incomplete or failing.",
        impaired=["global search", "SIEM search"],
        next_action="Inspect the OpenSearch container logs and cluster allocation, then retry.",
        detail=detail,
    )


async def _check_websocket(redis_ok: bool | None) -> dict:
    local_clients = ws_manager.local_connection_count()
    detail = {"backend": ws_manager.backend_name, "local_clients": local_clients}
    if ws_manager.backend_name != "redis":
        return _component(
            "websocket",
            "WebSocket",
            HEALTHY,
            f"In-process WebSocket hub with {local_clients} client(s) connected.",
            detail=detail,
        )
    if redis_ok is True:
        return _component(
            "websocket",
            "WebSocket",
            HEALTHY,
            f"Redis pub/sub is reachable; {local_clients} local client(s) connected.",
            detail=detail,
        )
    if redis_ok is False:
        return _component(
            "websocket",
            "WebSocket",
            DEGRADED,
            "Local WebSocket connections work, but Redis pub/sub is unreachable — live updates will not reach other instances.",
            impaired=["cross-instance live updates"],
            next_action="Restore Redis connectivity, then retry.",
            detail=detail,
        )
    return _component(
        "websocket",
        "WebSocket",
        UNKNOWN,
        "WebSocket hub is running but the pub/sub backend state could not be determined.",
        next_action="Verify Redis connectivity if a shared pub/sub backend is expected.",
        detail=detail,
    )


async def build_component_status() -> dict:
    """Full component health snapshot with an aggregate roll-up."""
    postgres = await _check_postgres()
    redis_component = await _check_redis()

    redis_ok: bool | None
    if not settings.redis_url:
        redis_ok = None
    elif redis_component["status"] == HEALTHY:
        redis_ok = True
    elif redis_component["status"] == UNAVAILABLE:
        redis_ok = False
    else:
        redis_ok = None

    queue_component = await _check_job_queue(redis_ok)
    search_component = await _check_search()
    websocket_component = await _check_websocket(redis_ok)

    api_component = _component(
        "api",
        "Backend API",
        HEALTHY,
        "This API process is handling requests.",
    )

    components = [
        api_component,
        postgres,
        redis_component,
        queue_component,
        search_component,
        websocket_component,
    ]

    order = {HEALTHY: 0, UNKNOWN: 1, DEGRADED: 2, UNAVAILABLE: 3}
    overall = max(components, key=lambda c: order.get(c["status"], 1))["status"]
    if overall == HEALTHY:
        overall = HEALTHY

    return {
        "overall": overall,
        "environment": settings.environment,
        "timestamp": _now(),
        "components": components,
    }
