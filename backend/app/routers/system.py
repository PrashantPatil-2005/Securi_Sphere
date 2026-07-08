"""System health and operational metrics for admin dashboard."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from app.brand import PRODUCT_NAME
from app.config import settings
from app.core.health import readiness
from app.database import get_db, get_db_read
from app.dependencies import require_roles
from app.jobs.queue import job_queue
from app.models.alert import Alert
from app.models.event import Event
from app.models.host import Host
from app.models.user import User
from app.search.opensearch_client import opensearch_cluster_health, opensearch_enabled
from app.websocket.manager import ws_manager

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health")
async def system_health(user: User = Depends(require_roles("admin"))):
    ready = await readiness()
    pending = await job_queue.pending_count()
    os_health = await opensearch_cluster_health() if settings.opensearch_url else None
    return {
        **ready,
        "environment": settings.environment,
        "search_backend": "opensearch" if opensearch_enabled() else "postgres",
        "opensearch": os_health,
        "job_queue_backend": job_queue.backend_name,
        "job_queue_running": job_queue.is_running,
        "job_queue_pending": pending,
        "job_queue_run_workers": settings.job_queue_run_workers,
        "ws_pubsub_backend": ws_manager.backend_name,
        "redis_configured": bool(settings.redis_url),
        "simulation_enabled": settings.enable_simulation,
        "registration_enabled": settings.allow_registration,
    }


@router.get("/pipeline")
async def pipeline_status(db=Depends(get_db_read), user: User = Depends(require_roles("admin"))):
    """QRadar-style 3-layer pipeline map for Securi."""
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    events_24h = (
        await db.execute(select(func.count()).select_from(Event).where(Event.timestamp >= since))
    ).scalar_one()
    flow_events_24h = (
        await db.execute(
            select(func.count()).select_from(Event).where(
                Event.timestamp >= since, Event.event_type == "network_flow"
            )
        )
    ).scalar_one()
    alerts_open = (
        await db.execute(select(func.count()).select_from(Alert).where(Alert.status == "open"))
    ).scalar_one()
    pending_jobs = await job_queue.pending_count()

    search_backend = "opensearch" if opensearch_enabled() else "postgres"
    broker_ok = job_queue.backend_name == "memory" or bool(settings.redis_url)

    return {
        "model": "ibm_qradar_3_layer",
        "description": "Event/flow collection → processing/rules → search → console",
        "layers": [
            {
                "layer": 1,
                "name": "Data Collection",
                "qradar_equivalent": "Event Collector + Flow Collector",
                "status": "ok",
                "components": [
                    {"id": "event_collector", "name": "Event Collector", "endpoint": "POST /api/v1/agent/events"},
                    {"id": "flow_collector", "name": "Flow Collector", "endpoint": "POST /api/v1/agent/flows"},
                    {"id": "windows_collector", "name": "Windows Event Forwarder", "endpoint": "POST /api/v1/agent/windows-events"},
                    {"id": "metrics_collector", "name": "Metrics Collector", "endpoint": "POST /api/v1/agent/metrics"},
                ],
                "functions": ["parsing", "normalization", "deduplication"],
                "stats": {"events_24h": events_24h, "flow_events_24h": flow_events_24h},
            },
            {
                "layer": 2,
                "name": "Data Processing",
                "qradar_equivalent": "Event Processor + Flow Processor",
                "status": "ok" if broker_ok else "degraded",
                "components": [
                    {"id": "detection", "name": "Detection rules", "path": "app.services.detection"},
                    {"id": "correlation", "name": "Correlation engine", "path": "app.services.correlation_engine"},
                    {"id": "offenses", "name": "Offense grouping", "path": "app.services.offense_engine"},
                    {"id": "job_queue", "name": "Job queue", "backend": job_queue.backend_name},
                    {"id": "ws_pubsub", "name": "WebSocket pub/sub", "backend": ws_manager.backend_name},
                ],
                "functions": ["storage", "custom_rules", "offense_grouping", "threat_scoring"],
                "stats": {"open_alerts": alerts_open, "pending_jobs": pending_jobs},
            },
            {
                "layer": 3,
                "name": "Data Search",
                "qradar_equivalent": "Search / Ariel (simplified)",
                "status": "ok",
                "components": [
                    {"id": "siem_search", "name": "SIEM query language", "endpoint": "GET /api/v1/search/siem"},
                    {"id": "global_search", "name": "Global search", "endpoint": "GET /api/v1/search"},
                    {"id": "events_api", "name": "Events API", "endpoint": "GET /api/v1/events"},
                ],
                "functions": ["full_text_search", "field_queries", "time_range_filters"],
                "stats": {"search_backend": search_backend},
            },
        ],
        "console": {
            "name": f"{PRODUCT_NAME} Console",
            "qradar_equivalent": "QRadar Console",
            "features": ["graphs", "reports", "alerts", "offenses", "investigations", "mitre"],
            "ui_routes": ["/", "/alerts", "/offenses", "/search", "/reports"],
        },
    }


@router.get("/stats")
async def system_stats(db=Depends(get_db_read), user: User = Depends(require_roles("admin"))):
    hosts_total = (await db.execute(select(func.count()).select_from(Host))).scalar_one()
    hosts_online = (
        await db.execute(select(func.count()).select_from(Host).where(Host.status == "online"))
    ).scalar_one()
    alerts_open = (
        await db.execute(select(func.count()).select_from(Alert).where(Alert.status == "open"))
    ).scalar_one()
    alerts_critical = (
        await db.execute(
            select(func.count()).select_from(Alert).where(Alert.status == "open", Alert.severity == "critical")
        )
    ).scalar_one()
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hosts_total": hosts_total,
        "hosts_online": hosts_online,
        "alerts_open": alerts_open,
        "alerts_critical": alerts_critical,
        "retention_days": settings.retention_days,
    }


@router.get("/circuits")
async def circuit_breaker_status(user: User = Depends(require_roles("admin"))):
    from app.core.circuit_breaker import all_breaker_snapshots

    return {
        "enabled": settings.circuit_breakers_enabled,
        "failure_threshold": settings.circuit_breaker_failure_threshold,
        "recovery_seconds": settings.circuit_breaker_recovery_seconds,
        "circuits": all_breaker_snapshots(),
    }


@router.get("/timeouts")
async def request_timeout_status(user: User = Depends(require_roles("admin"))):
    from app.core.http_timeouts import resolve_request_timeout

    return {
        "enabled": settings.request_timeout_enabled,
        "default_seconds": settings.request_timeout_seconds,
        "agent_seconds": settings.request_timeout_agent_seconds,
        "export_seconds": settings.request_timeout_export_seconds,
        "outbound_seconds": settings.outbound_http_timeout_seconds,
        "outbound_short_seconds": settings.outbound_http_timeout_short_seconds,
        "examples": {
            "api": resolve_request_timeout("/api/v1/alerts"),
            "agent": resolve_request_timeout("/api/v1/agent/events"),
            "export": resolve_request_timeout("/api/v1/events/export"),
            "health": resolve_request_timeout("/health/ready"),
        },
    }


@router.get("/pool")
async def database_pool_status_endpoint(
    api_replicas: int = 1,
    worker_replicas: int = 0,
    user: User = Depends(require_roles("admin")),
):
    from app.core.db_pool import database_pool_status, estimate_cluster_connections

    return {
        "primary": database_pool_status(role="primary"),
        "read": database_pool_status(role="read"),
        "cluster_estimate": estimate_cluster_connections(
            api_replicas=api_replicas,
            worker_replicas=worker_replicas,
        ),
    }


@router.get("/replicas")
async def read_replica_status_endpoint(user: User = Depends(require_roles("admin"))):
    from app.core.read_replica import read_replica_status

    status = await read_replica_status()
    return {
        **status,
        "read_url_configured": settings.read_replica_enabled,
        "routed_endpoints": [
            "GET /api/v1/analytics/*",
            "GET /api/v1/events",
            "GET /api/v1/search",
            "GET /api/v1/siem/*",
            "GET /api/v1/threat-scores",
            "GET /api/v1/mitre/*",
            "GET /api/v1/ueba/summary",
            "GET /api/v1/ueba/anomalies",
            "GET /api/v1/overview",
        ],
    }


@router.get("/analytics-mvs")
async def analytics_materialized_view_status(
    db=Depends(get_db_read),
    user: User = Depends(require_roles("admin")),
):
    from app.services.analytics.materialized_views import MV_NAMES, materialized_view_status

    views = await materialized_view_status(db)
    return {
        "enabled": settings.analytics_materialized_views_enabled,
        "refresh_interval_minutes": settings.analytics_mv_refresh_interval_minutes,
        "views": views,
        "expected": list(MV_NAMES),
    }


@router.post("/analytics-mvs/refresh")
async def refresh_analytics_materialized_views_endpoint(
    db=Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    from app.services.analytics.materialized_views import refresh_analytics_materialized_views

    if not settings.analytics_materialized_views_enabled:
        raise HTTPException(status_code=400, detail="Analytics materialized views are disabled")
    result = await refresh_analytics_materialized_views(db)
    await db.commit()
    return {"refreshed": result}


@router.post("/opensearch/backfill")
async def opensearch_backfill(
    event_limit: int = 10_000,
    alert_limit: int = 5000,
    user: User = Depends(require_roles("admin")),
):
    """Bulk reindex hosts, events, and alerts into OpenSearch (admin)."""
    if not settings.opensearch_url:
        raise HTTPException(status_code=400, detail="OPENSEARCH_URL is not configured")
    from app.services.opensearch_backfill import run_opensearch_backfill

    counts = await run_opensearch_backfill(event_limit=event_limit, alert_limit=alert_limit)
    return {"status": "ok", "indexed": counts, "search_backend": "opensearch"}
