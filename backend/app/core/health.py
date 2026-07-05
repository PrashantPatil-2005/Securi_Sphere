from datetime import datetime, timezone

from sqlalchemy import text

from app.database import async_session
from app.config import settings
from app.jobs.queue import job_queue
from app.jobs.redis_broker import redis_ping
from app.websocket.manager import ws_manager
from app.websocket.redis_pubsub import ws_pubsub_ping


async def liveness() -> dict:
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}


async def readiness() -> dict:
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
