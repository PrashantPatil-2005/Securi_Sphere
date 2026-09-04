"""Securi SIEM — Application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.brand import PRODUCT_NAME
from app.config import settings
from app.core.errors import http_exception_handler, validation_exception_handler, generic_exception_handler
from app.core.lifecycle import shutdown_application
from app.core.logging import configure_logging
from app.database import async_session
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_timeout import RequestTimeoutMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.request_context import RequestContextMiddleware
from app.routers import (
    agent, alerts, analytics, audit, auth, alert_rules, agent_bundle, backups, correlation_rules, events, health,
    hosts, incidents, investigation, ioc, maintenance, metrics, mitre, network, notifications, offenses, oidc,
    playbooks, reference_sets, building_blocks, reports, saved_searches, dashboard, search, siem,
    simulation, telemetry, threat_scores, timeline, ueba, settings as settings_router, system, users, ws,
    assistant,
)
from app.scheduler import scheduler, start_scheduler
from app.services.detection import seed_alert_rules
from app.services.migrate import migrate_schema
from app.services.mitre import seed_mitre
from app.services.correlation_engine import seed_correlation_rules
from app.websocket.manager import ws_manager

configure_logging()
logger = logging.getLogger(__name__)


async def init_db() -> None:
    await migrate_schema()
    async with async_session() as db:
        from app.routers.auth import seed_roles, seed_dev_users, seed_demo_users
        await seed_roles(db)
        await seed_dev_users(db)
        await seed_demo_users(db)
        await seed_alert_rules(db)
        await seed_mitre(db)
        await seed_correlation_rules(db)
        await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.testing:
        await init_db()
        from app.jobs.handlers import register_job_handlers
        register_job_handlers()
        from app.jobs.queue import job_queue
        job_queue.start()
        await ws_manager.start()
        start_scheduler()
    else:
        await init_db()
    logger.info(f"{PRODUCT_NAME} backend started", extra={"environment": settings.environment})
    yield
    if not settings.testing:
        await shutdown_application(scheduler=scheduler, job_queue=job_queue, ws_manager=ws_manager)
    else:
        from app.database import dispose_engines
        await dispose_engines()
    logger.info(f"{PRODUCT_NAME} backend shutdown complete")


def create_app() -> FastAPI:
    application = FastAPI(
        title=f"{PRODUCT_NAME} SIEM API",
        version="2.0.0",
        lifespan=lifespan,
        description="Production-grade security operations platform backend",
        docs_url="/docs" if settings.environment == "development" else None,
        redoc_url="/redoc" if settings.environment == "development" else None,
        openapi_url="/openapi.json" if settings.environment == "development" else None,
    )

    application.add_exception_handler(StarletteHTTPException, http_exception_handler)
    application.add_exception_handler(RequestValidationError, validation_exception_handler)
    application.add_exception_handler(Exception, generic_exception_handler)
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(RequestTimeoutMiddleware)
    application.add_middleware(RateLimitMiddleware)
    cors_origins = [settings.frontend_url]
    if settings.environment == "development":
        cors_origins.extend([
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3000",
        ])
    application.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    )

    prefix = "/api/v1"
    application.include_router(auth.router, prefix=prefix)
    application.include_router(oidc.router, prefix=prefix)
    application.include_router(hosts.router, prefix=prefix)
    application.include_router(agent.router, prefix=prefix)
    application.include_router(events.router, prefix=prefix)
    application.include_router(metrics.router, prefix=prefix)
    application.include_router(alerts.router, prefix=prefix)
    application.include_router(search.router, prefix=prefix)
    application.include_router(analytics.router, prefix=prefix)
    application.include_router(audit.router, prefix=prefix)
    application.include_router(backups.router, prefix=prefix)
    application.include_router(mitre.router, prefix=prefix)
    application.include_router(alert_rules.router, prefix=prefix)
    application.include_router(timeline.router, prefix=prefix)
    application.include_router(incidents.router, prefix=prefix)
    application.include_router(investigation.router, prefix=prefix)
    application.include_router(simulation.router, prefix=prefix)
    application.include_router(reports.router, prefix=prefix)
    application.include_router(network.router, prefix=prefix)
    application.include_router(threat_scores.router, prefix=prefix)
    application.include_router(siem.router, prefix=prefix)
    application.include_router(offenses.router, prefix=prefix)
    application.include_router(correlation_rules.router, prefix=prefix)
    application.include_router(maintenance.router, prefix=prefix)
    application.include_router(saved_searches.router, prefix=prefix)
    application.include_router(dashboard.router, prefix=prefix)
    application.include_router(settings_router.router, prefix=prefix)
    application.include_router(notifications.router, prefix=prefix)
    application.include_router(ioc.router, prefix=prefix)
    application.include_router(assistant.router, prefix=prefix)
    application.include_router(system.router, prefix=prefix)
    application.include_router(users.router, prefix=prefix)
    application.include_router(reference_sets.router, prefix=prefix)
    application.include_router(building_blocks.router, prefix=prefix)
    application.include_router(playbooks.router, prefix=prefix)
    application.include_router(ueba.router, prefix=prefix)
    application.include_router(telemetry.router, prefix=prefix)
    application.include_router(health.router)
    application.include_router(ws.router, prefix=prefix)
    application.include_router(agent_bundle.router)

    return application


app = create_app()
