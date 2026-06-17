import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from jose import JWTError
from sqlalchemy import select

from app.config import settings
from app.database import Base, async_session, engine
from app.routers import agent, alerts, analytics, audit, auth, alert_rules, events, hosts, incidents, metrics, mitre, network, offenses, reports, saved_searches, search, siem, simulation, threat_scores, timeline
from app.security import decode_token as jwt_decode
from app.middleware.rate_limit import RateLimitMiddleware
from app.services.detection import seed_alert_rules, update_host_statuses
from app.services.migrate import migrate_schema
from app.services.mitre import seed_mitre
from app.services.correlation_engine import seed_correlation_rules
from app.services.threat_score import update_all_threat_scores
from app.services.retention import run_retention
from app.websocket.manager import ws_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def init_db() -> None:
    await migrate_schema()
    async with async_session() as db:
        from app.routers.auth import seed_roles
        await seed_roles(db)
        await seed_alert_rules(db)
        await seed_mitre(db)
        await seed_correlation_rules(db)
        await db.commit()


async def status_job() -> None:
    async with async_session() as db:
        await update_host_statuses(db)
        await update_all_threat_scores(db)
        await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    scheduler.add_job(status_job, "interval", seconds=30, id="host_status")
    scheduler.add_job(run_retention, "cron", hour=2, id="retention")
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Mini SIEM API", version="1.0.0", lifespan=lifespan)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
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
app.include_router(saved_searches.router, prefix=prefix)


@app.get("/api/v1/overview")
async def overview():
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
        if payload.get("type") != "access":
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


@app.get("/install.sh")
async def serve_install_script():
    script = Path(__file__).resolve().parents[2] / "agent" / "install.sh"
    if not script.exists():
        script = Path(__file__).resolve().parents[1].parent / "agent" / "install.sh"
    return FileResponse(script, media_type="text/plain")


@app.get("/health")
async def health():
    return {"status": "ok"}
