from fastapi import APIRouter

from app.config import settings
from app.services.ai.llm import resolve_provider
from app.services.oidc import oidc_configured

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/public")
async def public_settings():
    return {
        "environment": settings.environment,
        "allow_registration": settings.allow_registration,
        "retention_days": settings.retention_days,
        "simulation_enabled": settings.enable_simulation,
        "demo_mode": settings.demo_mode,
        "exclude_simulated_from_dashboard": settings.exclude_simulated_from_dashboard,
        "oidc_enabled": oidc_configured(),
        "oidc_provider_label": settings.oidc_provider_label,
        "ai_assistant_enabled": settings.ai_assistant_enabled,
        "ai_provider": resolve_provider(),
        "search_backend": "opensearch" if settings.opensearch_url and settings.search_backend == "opensearch" else "postgres",
        "telemetry_enabled": settings.telemetry_enabled,
        "ux_flags": {
            "dynamic_ux_enabled": settings.dynamic_ux_enabled,
            "ux_activation_coach_enabled": settings.ux_activation_coach_enabled,
            "ux_live_simulation_enabled": settings.ux_live_simulation_enabled,
            "ux_enrollment_handshake_enabled": settings.ux_enrollment_handshake_enabled,
            "ux_guided_triage_enabled": settings.ux_guided_triage_enabled,
            "ux_dashboard_vitality_enabled": settings.ux_dashboard_vitality_enabled,
            "ux_admin_ops_console_enabled": settings.ux_admin_ops_console_enabled,
        },
    }
