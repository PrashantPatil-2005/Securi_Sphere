from datetime import datetime, timezone
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_host_by_api_key
from app.models.enrollment import EnrollmentToken
from app.models.event import Event
from app.models.host import Host
from app.models.metric import Metric
from app.schemas.agent import AgentRegisterRequest, AgentRegisterResponse, EventsBatch, MetricsBatch
from app.security import generate_api_key, hash_token
from app.services.agent_integrity import check_agent_integrity
from app.services.detection import check_service_failure_event, run_detection_for_host
from app.services.mitre import enrich_event
from app.services.correlation_engine import run_correlation_engine
from app.services.timeline import build_timelines
from app.services.threat_score import calculate_host_scores
from app.websocket.manager import ws_manager

router = APIRouter(prefix="/agent", tags=["agent"])


class HeartbeatPayload(BaseModel):
    agent_hash: str | None = None
    agent_version: str | None = None


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
    api_key = generate_api_key()
    host.api_key_hash = hash_token(api_key)
    host.hostname = body.hostname
    host.ip_address = body.ip_address
    host.os_info = body.os_info
    host.status = "online"
    host.last_seen = datetime.now(timezone.utc)
    enrollment.used_at = datetime.now(timezone.utc)
    return AgentRegisterResponse(api_key=api_key, host_id=host.id)


@router.post("/heartbeat")
async def heartbeat(
    body: HeartbeatPayload | None = None,
    host: Host = Depends(get_host_by_api_key),
    db: AsyncSession = Depends(get_db),
):
    host.last_seen = datetime.now(timezone.utc)
    if host.status == "offline":
        host.status = "online"
    if body:
        await check_agent_integrity(db, host, body.agent_hash, body.agent_version)
    return {"status": "ok"}


@router.post("/events")
async def ingest_events(
    body: EventsBatch,
    host: Host = Depends(get_host_by_api_key),
    db: AsyncSession = Depends(get_db),
):
    for item in body.events:
        event = Event(
            host_id=host.id,
            event_type=item.event_type,
            severity=item.severity,
            description=item.description,
            source=item.source,
            raw_log=item.raw_log,
            metadata_=item.metadata,
            timestamp=item.timestamp,
        )
        enrich_event(event)
        db.add(event)
        await check_service_failure_event(db, host, item.event_type)

    await db.flush()
    await run_detection_for_host(db, host)
    await run_correlation_engine(db, host.id)
    await build_timelines(db, host.id)
    await calculate_host_scores(db, host)
    for item in body.events:
        await ws_manager.broadcast({
            "type": "new_event",
            "data": {"host_id": str(host.id), "event_type": item.event_type, "severity": item.severity},
        })
    return {"ingested": len(body.events)}


@router.post("/metrics")
async def ingest_metrics(
    body: MetricsBatch,
    host: Host = Depends(get_host_by_api_key),
    db: AsyncSession = Depends(get_db),
):
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
    await db.flush()
    await run_detection_for_host(db, host)
    await calculate_host_scores(db, host)
    return {"ingested": len(body.metrics)}
