import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from jose import JWTError
from sqlalchemy import select
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.core.errors import http_exception_handler, validation_exception_handler
from app.core.health import liveness, readiness
from app.core.logging import configure_logging
from app.database import async_session, engine
from app.jobs.handlers import register_job_handlers
from app.jobs.queue import job_queue
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.request_context import RequestContextMiddleware
from app.routers import (
    agent, alerts, analytics, audit, auth, alert_rules, correlation_rules, events, hosts, incidents,
    maintenance, metrics, mitre, network, notifications, offenses, reports, saved_searches, search, siem,
    simulation, threat_scores, timeline, settings as settings_router, system,
)
from app.dependencies import get_current_user
from app.models.user import User
from app.security import create_ws_ticket, decode_token as jwt_decode
from app.services.correlation_engine import run_cross_host_correlation, seed_correlation_rules
from app.services.detection import seed_alert_rules, update_host_statuses
from app.services.migrate import migrate_schema
from app.services.mitre import seed_mitre
from app.services.retention import run_retention
from app.services.saved_search_alerts import run_saved_search_alerts
from app.services.threat_score import update_all_threat_scores
from app.services.analytics.aggregator import aggregate_daily_stats
from app.utils.agent_bundle import resolve_agent_bundle, resolve_install_script
from app.websocket.manager import ws_manager

configure_logging()
logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def init_db() -> None:
    await migrate_schema()
    async with async_session() as db:
        from app.routers.auth import seed_dev_users, seed_roles
        await seed_roles(db)
        await seed_dev_users(db)
        await seed_alert_rules(db)
        await seed_mitre(db)
        await seed_correlation_rules(db)
        await db.commit()


async def saved_search_job() -> None:
    async with async_session() as db:
        await run_saved_search_alerts(db)
        await db.commit()


async def status_job() -> None:
    async with async_session() as db:
        await update_host_statuses(db)
        await update_all_threat_scores(db)
        await db.commit()


async def analytics_job() -> None:
    async with async_session() as db:
        await aggregate_daily_stats(db)
        await db.commit()


async def cross_host_correlation_job() -> None:
    async with async_session() as db:
        await run_cross_host_correlation(db)
        await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    register_job_handlers()
    if not settings.testing:
        job_queue.start()
    await init_db()
    if not settings.testing:
        scheduler.add_job(status_job, "interval", seconds=30, id="host_status")
        scheduler.add_job(
            cross_host_correlation_job,
            "interval",
            seconds=settings.cross_host_correlation_interval_seconds,
            id="cross_host_correlation",
        )
        scheduler.add_job(run_retention, "cron", hour=2, id="retention")
        scheduler.add_job(analytics_job, "cron", hour=3, id="analytics")
        scheduler.add_job(saved_search_job, "interval", minutes=5, id="saved_search_alerts")
        scheduler.start()
    logger.info("SecuriSphere backend started", extra={"environment": settings.environment})
    yield
    if not settings.testing:
        scheduler.shutdown()
        await job_queue.stop()
    await engine.dispose()
    logger.info("SecuriSphere backend shutdown complete")


app = FastAPI(
    title="SecuriSphere SIEM API",
    version="2.0.0",
    lifespan=lifespan,
    description="Production-grade security operations platform backend",
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None,
    openapi_url="/openapi.json" if settings.environment == "development" else None,
)

app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

prefix = "/api/v1"
app.include_router(auth.router, prefix=prefix)
app.include_router(hosts.router, prefix=prefix)
app.include_router(agent.router, prefix=prefix)
app.include_router(events.router, prefix=prefix)
app.include_router(metrics.router, prefix=prefix)
app.include_router(alerts.router, prefix=prefix)
app.include_router(search.router, prefix=prefix)
app.include_router(analytics.router, prefix=prefix)
app.include_router(audit.router, prefix=prefix)
app.include_router(mitre.router, prefix=prefix)
app.include_router(alert_rules.router, prefix=prefix)
app.include_router(timeline.router, prefix=prefix)
app.include_router(incidents.router, prefix=prefix)
app.include_router(simulation.router, prefix=prefix)
app.include_router(reports.router, prefix=prefix)
app.include_router(network.router, prefix=prefix)
app.include_router(threat_scores.router, prefix=prefix)
app.include_router(siem.router, prefix=prefix)
app.include_router(offenses.router, prefix=prefix)
app.include_router(correlation_rules.router, prefix=prefix)
app.include_router(maintenance.router, prefix=prefix)
app.include_router(saved_searches.router, prefix=prefix)
app.include_router(settings_router.router, prefix=prefix)
app.include_router(notifications.router, prefix=prefix)
app.include_router(system.router, prefix=prefix)


@app.get("/health")
async def health():
    return await liveness()


@app.get("/health/live")
async def health_live():
    return await liveness()


@app.get("/health/ready")
async def health_ready():
    return await readiness()


@app.get("/api/v1/overview")
async def overview(user: User = Depends(get_current_user)):
    from sqlalchemy import func
    from app.models.alert import Alert
    from app.models.host import Host

    async with async_session() as db:
        total = (await db.execute(select(func.count()).select_from(Host))).scalar_one()
        online = (await db.execute(select(func.count()).select_from(Host).where(Host.status == "online"))).scalar_one()
        offline = (await db.execute(select(func.count()).select_from(Host).where(Host.status.in_(["offline", "critical"])))).scalar_one()
        active = (await db.execute(select(func.count()).select_from(Alert).where(Alert.status == "open"))).scalar_one()
        critical = (await db.execute(select(func.count()).select_from(Alert).where(Alert.status == "open", Alert.severity == "critical"))).scalar_one()
    return {
        "total_hosts": total,
        "online_hosts": online,
        "offline_hosts": offline,
        "active_alerts": active,
        "critical_alerts": critical,
    }


@app.websocket("/api/v1/ws")
async def websocket_endpoint(websocket: WebSocket, token: str | None = None):
    if not token:
        await websocket.close(code=4001)
        return
    try:
        payload = jwt_decode(token)
        if payload.get("type") not in ("access", "ws"):
            await websocket.close(code=4001)
            return
    except JWTError:
        await websocket.close(code=4001)
        return

    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@app.post("/api/v1/ws/token")
async def ws_token(user: User = Depends(get_current_user)):
    return {"token": create_ws_ticket(str(user.id)), "expires_in": 60}


@app.get("/install.sh")
async def serve_install_script():
    return FileResponse(resolve_install_script(), media_type="text/x-shellscript", filename="install.sh")


@app.get("/agent-bundle.tar.gz")
async def serve_agent_bundle():
    bundle = resolve_agent_bundle()
    return FileResponse(bundle, media_type="application/gzip", filename="agent-bundle.tar.gz")
