from datetime import datetime, timezone
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import host_id_var
from app.database import get_db
from app.dependencies_agent import AuthenticatedAgent, get_authenticated_agent
from app.models.enrollment import EnrollmentToken
from app.models.host import Host
from app.models.metric import Metric
from app.schemas.agent import AgentRegisterRequest, AgentRegisterResponse, EventsBatch, MetricsBatch
from app.security import generate_api_key, hash_token
from app.services.agent_integrity import check_agent_integrity
from app.services.audit import log_audit
from app.services.detection import run_detection_for_host
from app.services.threat_score import calculate_host_scores
from app.pipeline.ingestion import ingest_event_batch

router = APIRouter(prefix="/agent", tags=["agent"])


class HeartbeatPayload(BaseModel):
    agent_hash: str | None = None
    agent_version: str | None = None


class EventsIngestResponse(BaseModel):
    ingested: int
    deduplicated: int = 0
    errors: list[str] = []


@router.post("/register", response_model=AgentRegisterResponse)
async def register_agent(body: AgentRegisterRequest, db: AsyncSession = Depends(get_db)):
    token_hash = hash_token(body.enrollment_token)
    result = await db.execute(
        select(EnrollmentToken).where(
            EnrollmentToken.token_hash == token_hash,
            EnrollmentToken.used_at.is_(None),
            EnrollmentToken.revoked_at.is_(None),
            EnrollmentToken.expires_at > datetime.now(timezone.utc),
        )
    )
    enrollment = result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=400, detail="Invalid, expired, or revoked enrollment token")

    host_result = await db.execute(select(Host).where(Host.id == enrollment.host_id))
    host = host_result.scalar_one()

    was_enrolled = bool(host.api_key_hash)
    api_key = generate_api_key()
    host.api_key_hash = hash_token(api_key)
    host.api_key_created_at = datetime.now(timezone.utc)
    host.api_key_revoked_at = None
    host.hostname = body.hostname
    host.ip_address = body.ip_address
    host.os_info = body.os_info
    host.status = "online"
    host.last_seen = datetime.now(timezone.utc)
    enrollment.used_at = datetime.now(timezone.utc)

    if was_enrolled:
        await log_audit(
            db,
            "agent_reregister",
            resource_type="host",
            resource_id=host.id,
            details={"hostname": body.hostname},
        )

    if body.agent_hash:
        await check_agent_integrity(db, host, body.agent_hash, body.agent_version)

    return AgentRegisterResponse(api_key=api_key, host_id=host.id)


@router.post("/heartbeat")
async def heartbeat(
    auth: AuthenticatedAgent = Depends(get_authenticated_agent),
    db: AsyncSession = Depends(get_db),
):
    host = auth.host
    host_id_var.set(str(host.id))
    host.last_seen = datetime.now(timezone.utc)

    payload = HeartbeatPayload.model_validate(auth.parse_json()) if auth.raw_body else HeartbeatPayload()
    if host.status in ("offline", "critical", "warning"):
        host.status = "online"
    if payload.agent_hash or payload.agent_version:
        await check_agent_integrity(db, host, payload.agent_hash, payload.agent_version)
    return {"status": "ok"}


@router.post("/events", response_model=EventsIngestResponse)
async def ingest_events(
    auth: AuthenticatedAgent = Depends(get_authenticated_agent),
    db: AsyncSession = Depends(get_db),
):
    host = auth.host
    host_id_var.set(str(host.id))
    body = EventsBatch.model_validate_json(auth.raw_body)
    ingested, errors, deduplicated = await ingest_event_batch(db, host, body.events)
    if ingested:
        await run_detection_for_host(db, host)
    return EventsIngestResponse(ingested=len(ingested), deduplicated=deduplicated, errors=errors)


@router.post("/metrics")
async def ingest_metrics(
    auth: AuthenticatedAgent = Depends(get_authenticated_agent),
    db: AsyncSession = Depends(get_db),
):
    host = auth.host
    host_id_var.set(str(host.id))
    body = MetricsBatch.model_validate_json(auth.raw_body)
    for item in body.metrics:
        db.add(Metric(
            host_id=host.id,
            cpu_percent=item.cpu_percent,
            memory_percent=item.memory_percent,
            disk_percent=item.disk_percent,
            network_in=item.network_in,
            network_out=item.network_out,
            load_average=item.load_average,
            uptime_seconds=item.uptime_seconds,
            recorded_at=item.recorded_at,
        ))
    host.last_seen = datetime.now(timezone.utc)
    if host.status in ("offline", "critical", "warning"):
        host.status = "online"
    await db.flush()
    await run_detection_for_host(db, host)
    await calculate_host_scores(db, host)
    return {"ingested": len(body.metrics)}


@router.post("/rotate-key")
async def rotate_api_key(
    auth: AuthenticatedAgent = Depends(get_authenticated_agent),
    db: AsyncSession = Depends(get_db),
):
    """Rotate agent API key. Old key is immediately revoked."""
    host = auth.host
    new_key = generate_api_key()
    host.api_key_hash = hash_token(new_key)
    host.api_key_created_at = datetime.now(timezone.utc)
    host.api_key_revoked_at = None
    return {"api_key": new_key, "rotated_at": host.api_key_created_at.isoformat()}
