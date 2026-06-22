from fastapi import APIRouter

from app.config import settings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/public")
async def public_settings():
    return {
        "environment": settings.environment,
        "allow_registration": settings.allow_registration,
        "retention_days": settings.retention_days,
        "simulation_enabled": settings.enable_simulation,
        "exclude_simulated_from_dashboard": settings.exclude_simulated_from_dashboard,
    }
