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
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.jobs.queue import JobPriority, job_queue
from app.models.event import Event
from app.models.host import Host
from app.pipeline.normalizer import build_normalized_event, normalize_event_type
from app.pipeline.validator import ValidationError, validate_batch_size, validate_event_payload
from app.schemas.agent import EventIngest
from app.services.mitre import enrich_event
from app.services.offense_engine import link_event_to_offense
from app.websocket.manager import ws_manager

logger = logging.getLogger(__name__)

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
    validate_batch_size(len(events))
    ingested: list[Event] = []
    errors: list[str] = []
    deduplicated = 0

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
        if await is_duplicate(db, fp):
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
            source_ip=normalized.get("source_ip"),
            username=normalized.get("username"),
            category=normalized.get("category"),
            timestamp=item.timestamp,
        )
        enrich_event(event)
        db.add(event)
        ingested.append(event)

        from app.services.detection import check_service_failure_event
        await check_service_failure_event(db, host, normalized_type)

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
        await check_reference_intel_on_event(db, host, event)

    host.last_seen = datetime.now(timezone.utc)

    if async_pipeline and settings.async_event_pipeline:
        await job_queue.enqueue(
            "correlation_pipeline",
            {"host_id": str(host.id)},
            priority=JobPriority.HIGH,
        )
    else:
        from app.pipeline.processor import run_post_ingestion_pipeline
        await run_post_ingestion_pipeline(db, host.id)

    for event in ingested:
        await link_event_to_offense(db, event)
        await ws_manager.broadcast({
            "type": "security_feed",
            "data": {
                "id": str(event.id),
                "host_id": str(host.id),
                "host_name": host.name,
                "event_type": event.event_type,
                "severity": event.severity,
                "category": event.category,
                "username": event.username,
                "source_ip": event.source_ip,
                "description": event.description,
                "timestamp": event.timestamp.isoformat(),
                "normalized_event": event.normalized_event,
            },
        })

    from app.search.indexer import index_events_batch

    await index_events_batch(ingested, {host.id: host.name})

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
