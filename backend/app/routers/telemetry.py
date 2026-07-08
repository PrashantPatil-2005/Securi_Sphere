"""Product telemetry ingestion for funnel and UX analytics."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import client_ip, get_current_user, require_roles
from app.models.telemetry_event import TelemetryEvent
from app.models.user import User

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

ALLOWED_EVENTS = frozenset({
    "auth_register_complete",
    "auth_login_success",
    "invite_accepted",
    "onboarding_step_viewed",
    "onboarding_step_completed",
    "onboarding_dismissed",
    "activation_coach_shown",
    "activation_coach_action",
    "demo_banner_viewed",
    "demo_banner_dismissed",
    "demo_banner_clicked",
    "simulation_started",
    "simulation_stage",
    "simulation_completed",
    "guided_step_clicked",
    "host_enrollment_started",
    "host_enrollment_success",
    "alert_triage_started",
    "alert_triage_resolved",
    "offense_promoted",
    "workspace_opened",
    "search_executed",
    "notification_channel_enabled",
    "ai_assistant_opened",
    "ai_assistant_message_sent",
    "admin_ops_action",
    "rule_tuning_action",
    "intel_feed_sync",
    "page_dwell",
})


class TelemetryEventIn(BaseModel):
    event: str = Field(..., max_length=100)
    properties: dict | None = None
    session_id: str | None = Field(None, max_length=64)
    page_path: str | None = Field(None, max_length=255)


@router.post("/events", status_code=204)
async def ingest_event(
    body: TelemetryEventIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not settings.telemetry_enabled:
        return Response(status_code=204)

    if body.event not in ALLOWED_EVENTS:
        return Response(status_code=204)

    entry = TelemetryEvent(
        user_id=user.id,
        event=body.event,
        properties=body.properties,
        session_id=body.session_id,
        page_path=body.page_path,
        ip_address=client_ip(request),
        request_id=getattr(request.state, "request_id", None),
    )
    db.add(entry)
    await db.commit()
    return Response(status_code=204)


@router.get("/summary")
async def telemetry_summary(
    days: int = 7,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst")),
):
    if not settings.telemetry_enabled:
        return {"enabled": False, "days": days, "events": [], "funnel": {}}

    since = datetime.now(timezone.utc) - timedelta(days=max(1, min(days, 90)))
    rows = (
        await db.execute(
            select(TelemetryEvent.event, func.count())
            .where(TelemetryEvent.created_at >= since)
            .group_by(TelemetryEvent.event)
            .order_by(func.count().desc())
        )
    ).all()

    counts = {event: count for event, count in rows}
    funnel_keys = [
        "auth_register_complete",
        "simulation_completed",
        "host_enrollment_success",
        "alert_triage_resolved",
        "offense_promoted",
    ]
    return {
        "enabled": True,
        "days": days,
        "events": [{"event": e, "count": c} for e, c in rows],
        "funnel": {k: counts.get(k, 0) for k in funnel_keys},
        "total": sum(counts.values()),
    }
