"""Event ingestion pipeline — the entry point for all security events.

Flow:
  Agent POST /api/v1/agent/events
    → validate_batch_size (1-100 events)
    → for each event:
        → validate_event_payload (type, severity, timestamp, field lengths)
        → normalize_event_type (aliases → canonical names)
        → event_fingerprint + is_duplicate (deduplication)
        → build_normalized_event (extract source_ip, username, category)
        → enrich_event (MITRE ATT&CK mapping)
        → check_reference_intel_on_event (IOC matching)
        → check_service_failure_event (immediate alert trigger)
    → db.flush()
    → enqueue async correlation pipeline (or run sync)
    → broadcast via WebSocket (real-time feed)
    → index in OpenSearch (if enabled)

Security controls:
  - Timestamp validation: rejects events > 5 min in future or > 30 days old
  - Batch size limit: max 100 events per request
  - Field length limits: max 8192 chars for strings
  - Deduplication: SHA-256 fingerprint prevents re-ingestion
  - HMAC signing: agent signs each request (optional, prevents replay)

Backpressure:
  - Ingestion semaphore limits concurrent database writes
  - When capacity is exhausted, clients receive 429 (Too Many Requests)
  - Protects database pool from being saturated by agent bursts
"""

import asyncio
import logging
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.jobs.queue import JobPriority, job_queue
from app.models.event import Event
from app.models.host import Host
from app.pipeline.event_payload import ip_from_raw_log, safe_inet
from app.pipeline.normalizer import build_normalized_event, normalize_event_type
from app.pipeline.validator import ValidationError, validate_batch_size, validate_event_payload
from app.schemas.agent import EventIngest
from app.services.mitre import enrich_event
from app.services.offense_engine import link_event_to_offense
from app.websocket.manager import ws_manager

logger = logging.getLogger(__name__)

# Backpressure: limit concurrent ingestion to protect the database pool
MAX_CONCURRENT_INGESTION = 20
_ingestion_semaphore = asyncio.Semaphore(MAX_CONCURRENT_INGESTION)

# Performance counter — tracks events/second across the lifetime of the process
_INGESTION_COUNTER = {
    "total_events": 0,
    "total_batches": 0,
    "total_errors": 0,
    "total_deduplicated": 0,
    "total_seconds": 0.0,
}


async def ingest_event_batch(
    db: AsyncSession,
    host: Host,
    events: list[EventIngest],
    *,
    async_pipeline: bool = True,
) -> tuple[list[Event], list[str], int]:
    if not _ingestion_semaphore.locked():
        pass  # capacity available
    else:
        acquired = await asyncio.wait_for(_ingestion_semaphore.acquire(), timeout=5.0) if not _ingestion_semaphore.locked() else False
        if not acquired:
            raise HTTPException(status_code=429, detail="Ingestion capacity exhausted — retry later")
        _ingestion_semaphore.release()

    async with _ingestion_semaphore:
        return await _ingest_event_batch_inner(db, host, events, async_pipeline=async_pipeline)


async def _ingest_event_batch_inner(
    db: AsyncSession,
    host: Host,
    events: list[EventIngest],
    *,
    async_pipeline: bool = True,
) -> tuple[list[Event], list[str], int]:
    try:
        validate_batch_size(len(events))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc
    ingested: list[Event] = []
    errors: list[str] = []
    deduplicated = 0
    batch_start = datetime.now(timezone.utc)

    for idx, item in enumerate(events):
        try:
            validate_event_payload(
                item.event_type,
                item.severity,
                item.timestamp,
                item.description,
                item.raw_log,
                item.metadata,
            )
        except ValidationError as exc:
            errors.append(f"event[{idx}]: {exc.message}")
            continue

        normalized_type = normalize_event_type(item.event_type)

        from app.services.ingest_dedup import event_fingerprint, is_duplicate
        fp = event_fingerprint(host.id, item.timestamp, normalized_type, item.raw_log)
        with db.no_autoflush:
            duplicate = await is_duplicate(db, fp)
        if duplicate:
            deduplicated += 1
            continue

        normalized = build_normalized_event(
            event_id=None,
            timestamp=item.timestamp,
            host_id=host.id,
            event_type=normalized_type,
            severity=item.severity,
            description=item.description,
            source=item.source,
            raw_log=item.raw_log,
            metadata=item.metadata,
        )

        event = Event(
            host_id=host.id,
            event_type=normalized_type,
            severity=item.severity,
            description=item.description,
            source=item.source,
            raw_log=item.raw_log,
            raw_event=item.raw_log,
            metadata_=item.metadata,
            normalized_event=normalized,
            source_ip=safe_inet(normalized.get("source_ip")) or ip_from_raw_log(item.raw_log),
            username=(str(normalized["username"])[:255] if normalized.get("username") else None),
            category=normalized.get("category"),
            timestamp=item.timestamp,
        )
        enrich_event(event)
        db.add(event)
        ingested.append(event)

        from app.services.detection import check_service_failure_event
        try:
            await check_service_failure_event(db, host, normalized_type)
        except Exception:
            logger.exception(
                "service-failure detection failed",
                extra={"host_id": str(host.id), "event_type": normalized_type},
            )

    if not ingested:
        return ingested, errors, deduplicated

    await db.flush()

    for event in ingested:
        event.normalized_event = build_normalized_event(
            event_id=event.id,
            timestamp=event.timestamp,
            host_id=host.id,
            event_type=event.event_type,
            severity=event.severity,
            description=event.description,
            source=event.source,
            raw_log=event.raw_log,
            metadata=event.metadata_,
        )
        from app.services.reference_intel_detection import check_reference_intel_on_event
        try:
            await check_reference_intel_on_event(db, host, event)
        except Exception:
            logger.exception("reference intel check failed", extra={"event_id": str(event.id)})

    host.last_seen = datetime.now(timezone.utc)

    if async_pipeline and settings.async_event_pipeline:
        try:
            await job_queue.enqueue(
                "correlation_pipeline",
                {"host_id": str(host.id)},
                priority=JobPriority.HIGH,
            )
        except Exception:
            logger.exception(
                "failed to enqueue correlation pipeline — events are persisted",
                extra={"host_id": str(host.id)},
            )
    else:
        from app.pipeline.processor import run_post_ingestion_pipeline
        await run_post_ingestion_pipeline(db, host.id)

    for event in ingested:
        try:
            await link_event_to_offense(db, event)
        except Exception:
            logger.exception(
                "offense linking failed — event remains stored",
                extra={"event_id": str(event.id), "event_type": event.event_type},
            )

    # Record post-commit side effects (outbox pattern)
    if "post_commit_hooks" not in db.info:
        db.info["post_commit_hooks"] = []
    hooks: list = db.info["post_commit_hooks"]

    _host_id = host.id
    _host_name = host.name
    _event_snapshots = [
        {
            "id": str(event.id),
            "host_id": str(_host_id),
            "host_name": _host_name,
            "event_type": event.event_type,
            "severity": event.severity,
            "category": event.category,
            "username": event.username,
            "source_ip": event.source_ip,
            "description": event.description,
            "timestamp": event.timestamp.isoformat(),
            "normalized_event": event.normalized_event,
        }
        for event in ingested
    ]

    async def _post_commit():
        for snap in _event_snapshots:
            try:
                await ws_manager.broadcast({"type": "security_feed", "data": snap})
            except Exception:
                pass
        try:
            from app.search.indexer import index_events_batch
            await index_events_batch(ingested, {_host_id: _host_name})
        except Exception:
            pass

    hooks.append(_post_commit)

    # Performance metrics
    _INGESTION_COUNTER["total_events"] += len(ingested)
    _INGESTION_COUNTER["total_batches"] += 1
    _INGESTION_COUNTER["total_errors"] += len(errors)
    _INGESTION_COUNTER["total_deduplicated"] += deduplicated

    elapsed = (datetime.now(timezone.utc) - batch_start).total_seconds()
    _INGESTION_COUNTER["total_seconds"] += elapsed

    if _INGESTION_COUNTER["total_events"] > 0:
        eps = _INGESTION_COUNTER["total_events"] / max(_INGESTION_COUNTER["total_seconds"], 0.001)
    else:
        eps = 0

    logger.info(
        "events ingested",
        extra={
            "host_id": str(host.id),
            "count": len(ingested),
            "errors": len(errors),
            "deduplicated": deduplicated,
            "elapsed_ms": round(elapsed * 1000, 1),
            "events_per_second": round(eps, 1),
            "total_events": _INGESTION_COUNTER["total_events"],
        },
    )
    return ingested, errors, deduplicated
