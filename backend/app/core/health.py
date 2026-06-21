from datetime import datetime, timezone

from sqlalchemy import text

from app.database import async_session
from app.jobs.queue import job_queue


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
    ready = all(v == "ok" for v in checks.values())
    return {
        "status": "ready" if ready else "degraded",
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
