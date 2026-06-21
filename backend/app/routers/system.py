"""System health and operational metrics for admin dashboard."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.config import settings
from app.core.health import readiness
from app.database import get_db
from app.dependencies import require_roles
from app.jobs.queue import job_queue
from app.models.alert import Alert
from app.models.host import Host
from app.models.user import User

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health")
async def system_health(user: User = Depends(require_roles("admin"))):
    ready = await readiness()
    return {
        **ready,
        "environment": settings.environment,
        "job_queue_running": job_queue.is_running,
        "redis_configured": bool(settings.redis_url),
        "simulation_enabled": settings.enable_simulation,
        "registration_enabled": settings.allow_registration,
    }


@router.get("/stats")
async def system_stats(db=Depends(get_db), user: User = Depends(require_roles("admin"))):
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
