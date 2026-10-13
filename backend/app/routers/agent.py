from datetime import datetime, timezone
import json
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import host_id_var
from app.database import get_db
from app.dependencies_agent import AuthenticatedAgent, get_authenticated_agent
from app.models.enrollment import EnrollmentToken
from app.models.host import Host
from app.models.metric import Metric
from app.schemas.agent import AgentRegisterRequest, AgentRegisterResponse, FlowsBatch, MetricsBatch, WindowsEventsBatch
from app.security import generate_api_key, hash_token
from app.services.agent_integrity import check_agent_integrity
from app.services.audit import log_audit
from app.pipeline.event_payload import coerce_event_ingests, parse_events_body
from app.pipeline.ingestion import ingest_event_batch
from app.pipeline.flow_collector import flows_to_events
from app.pipeline.windows_collector import windows_events_to_ingest
from app.services.host_notify import broadcast_host_update

router = APIRouter(prefix="/agent", tags=["agent"])


class HeartbeatPayload(BaseModel):
    agent_hash: str | None = None
    agent_version: str | None = None
    flows_enabled: bool | None = None
    delivery: dict | None = None


DELIVERY_INT_FIELDS = (
    "buffered_events",
    "consecutive_failures",
    "dropped_events",
)
DELIVERY_STR_FIELDS = (
    "last_flush_at",
    "last_success_at",
)


def sanitize_delivery_stats(raw: dict | None) -> dict | None:
    """Keep only known scalar fields from the agent's delivery block.

    Agents are untrusted inputs: accept bounded ints and short strings only.
    No raw logs or free-form content is stored.
    """
    if not isinstance(raw, dict):
        return None
    out: dict = {}
    for key in DELIVERY_INT_FIELDS:
        value = raw.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            continue
        if value < 0 or value > 10_000_000:
            continue
        out[key] = value
    for key in DELIVERY_STR_FIELDS:
        value = raw.get(key)
        if isinstance(value, str) and 0 < len(value) <= 40:
            out[key] = value
    auth_failed = raw.get("auth_failed")
    if isinstance(auth_failed, bool):
        out["auth_failed"] = auth_failed
    if not out:
        return None
    out["reported_at"] = datetime.now(timezone.utc).isoformat()
    return out


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

    await db.flush()
    from app.search.indexer import index_host
    await index_host(host)
    await broadcast_host_update(host, "host_enrolled" if not was_enrolled else "host_status")

    return AgentRegisterResponse(api_key=api_key, host_id=host.id)


@router.post("/heartbeat")
async def heartbeat(
    auth: AuthenticatedAgent = Depends(get_authenticated_agent),
    db: AsyncSession = Depends(get_db),
):
    host = auth.host
    host_id_var.set(str(host.id))
    host.last_seen = datetime.now(timezone.utc)

    try:
        payload = HeartbeatPayload.model_validate(auth.parse_json()) if auth.raw_body else HeartbeatPayload()
    except (PydanticValidationError, ValueError, TypeError, json.JSONDecodeError):
        payload = HeartbeatPayload()
    status_changed = False
    if host.status in ("offline", "critical", "warning"):
        host.status = "online"
        status_changed = True
    if payload.agent_hash or payload.agent_version:
        await check_agent_integrity(db, host, payload.agent_hash, payload.agent_version)
    delivery = sanitize_delivery_stats(payload.delivery)
    if delivery is not None:
        host.delivery_stats = delivery
    if payload.flows_enabled is not None:
        stats = dict(host.delivery_stats or {})
        stats["flows_enabled"] = bool(payload.flows_enabled)
        host.delivery_stats = stats
    if status_changed:
        await db.flush()
        from app.search.indexer import index_host
        await index_host(host)
    return {"status": "ok"}


@router.post("/events", response_model=EventsIngestResponse)
async def ingest_events(
    auth: AuthenticatedAgent = Depends(get_authenticated_agent),
    db: AsyncSession = Depends(get_db),
):
    host = auth.host
    host_id_var.set(str(host.id))
    items, body_error = parse_events_body(auth.raw_body)
    if body_error:
        raise HTTPException(status_code=422, detail=body_error)
    events, parse_errors = coerce_event_ingests(items or [])
    if not events:
        return EventsIngestResponse(ingested=0, deduplicated=0, errors=parse_errors or ["no valid events"])
    ingested, errors, deduplicated = await ingest_event_batch(db, host, events)
    return EventsIngestResponse(
        ingested=len(ingested),
        deduplicated=deduplicated,
        errors=parse_errors + errors,
    )


@router.post("/flows", response_model=EventsIngestResponse)
async def ingest_flows(
    auth: AuthenticatedAgent = Depends(get_authenticated_agent),
    db: AsyncSession = Depends(get_db),
):
    """Layer 1 flow collector — network flows normalized into searchable events."""
    host = auth.host
    host_id_var.set(str(host.id))
    try:
        body = FlowsBatch.model_validate_json(auth.raw_body)
    except PydanticValidationError as exc:
        raise HTTPException(status_code=422, detail="Invalid flows payload") from exc
    events = flows_to_events(body.flows)
    ingested, errors, deduplicated = await ingest_event_batch(db, host, events)
    return EventsIngestResponse(ingested=len(ingested), deduplicated=deduplicated, errors=errors)


@router.post("/windows-events", response_model=EventsIngestResponse)
async def ingest_windows_events(
    auth: AuthenticatedAgent = Depends(get_authenticated_agent),
    db: AsyncSession = Depends(get_db),
):
    """Windows Event Log / Sysmon forwarder (spike)."""
    host = auth.host
    host_id_var.set(str(host.id))
    try:
        body = WindowsEventsBatch.model_validate_json(auth.raw_body)
    except PydanticValidationError as exc:
        raise HTTPException(status_code=422, detail="Invalid windows-events payload") from exc
    events = windows_events_to_ingest(body.events)
    ingested, errors, deduplicated = await ingest_event_batch(db, host, events)
    return EventsIngestResponse(ingested=len(ingested), deduplicated=deduplicated, errors=errors)


@router.post("/metrics")
async def ingest_metrics(
    auth: AuthenticatedAgent = Depends(get_authenticated_agent),
    db: AsyncSession = Depends(get_db),
):
    host = auth.host
    host_id_var.set(str(host.id))
    try:
        body = MetricsBatch.model_validate_json(auth.raw_body)
    except PydanticValidationError as exc:
        raise HTTPException(status_code=422, detail="Invalid metrics payload") from exc
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

    from app.jobs.queue import job_queue, JobPriority
    host_id_str = str(host.id)
    await job_queue.enqueue(
        "detection_and_scores",
        {"host_id": host_id_str},
        priority=JobPriority.NORMAL,
    )
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
