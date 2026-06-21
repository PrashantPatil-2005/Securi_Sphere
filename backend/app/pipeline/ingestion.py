"""Event ingestion orchestrator."""

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


async def ingest_event_batch(
    db: AsyncSession,
    host: Host,
    events: list[EventIngest],
    *,
    async_pipeline: bool = True,
) -> tuple[list[Event], list[str]]:
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

    logger.info(
        "events ingested",
        extra={"host_id": str(host.id), "count": len(ingested), "errors": len(errors), "deduplicated": deduplicated},
    )
    return ingested, errors, deduplicated
