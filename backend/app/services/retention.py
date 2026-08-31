import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select

from app.config import settings
from app.database import async_session
from app.models.alert import Alert
from app.models.audit import AuditLog
from app.models.correlation import CorrelationResult
from app.models.event import Event
from app.models.ingest_dedup import IngestDedup
from app.models.metric import Metric
from app.models.timeline import AttackTimeline

logger = logging.getLogger(__name__)

RETENTION_BATCH_SIZE = 5000


async def _batch_delete(db, model, column, cutoff) -> int:
    """Delete old rows in batches to avoid locking the table."""
    pk_col = model.__table__.primary_key.columns.values()[0]
    total_deleted = 0
    while True:
        subq = (
            select(pk_col)
            .where(column < cutoff)
            .limit(RETENTION_BATCH_SIZE)
            .subquery()
        )
        result = await db.execute(
            delete(model).where(pk_col.in_(select(subq.c[pk_col.name])))
        )
        deleted = result.rowcount
        total_deleted += deleted
        if deleted < RETENTION_BATCH_SIZE:
            break
    return total_deleted


async def run_retention() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.retention_days)
    dedup_cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.idempotency_ttl_seconds)
    async with async_session() as db:
        await _batch_delete(db, Event, Event.timestamp, cutoff)
        await _batch_delete(db, Metric, Metric.recorded_at, cutoff)
        await _batch_delete(db, AttackTimeline, AttackTimeline.created_at, cutoff)
        await _batch_delete(db, CorrelationResult, CorrelationResult.detected_at, cutoff)

        resolved_cutoff = cutoff
        alert_deleted = 0
        while True:
            subq = (
                select(Alert.id)
                .where(Alert.created_at < resolved_cutoff, Alert.status.in_(["resolved", "closed"]))
                .limit(RETENTION_BATCH_SIZE)
                .subquery()
            )
            result = await db.execute(
                delete(Alert).where(Alert.id.in_(select(subq.c.id)))
            )
            alert_deleted += result.rowcount
            if result.rowcount < RETENTION_BATCH_SIZE:
                break

        if not settings.audit_immutable:
            audit_cutoff = datetime.now(timezone.utc) - timedelta(days=settings.audit_retention_days)
            await _batch_delete(db, AuditLog, AuditLog.timestamp, audit_cutoff)

        await _batch_delete(db, IngestDedup, IngestDedup.created_at, dedup_cutoff)

        await db.commit()
    if settings.event_partitioning_enabled:
        from app.services.event_partitions import drop_old_event_partitions, ensure_event_partitions

        await drop_old_event_partitions(cutoff)
        await ensure_event_partitions()
    logger.info("Retention completed: cutoff %s days", settings.retention_days)
