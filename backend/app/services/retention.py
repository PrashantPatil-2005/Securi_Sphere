import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete

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


async def run_retention() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.retention_days)
    dedup_cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.idempotency_ttl_seconds)
    async with async_session() as db:
        await db.execute(delete(Event).where(Event.timestamp < cutoff))
        await db.execute(delete(Metric).where(Metric.recorded_at < cutoff))
        await db.execute(delete(Alert).where(Alert.created_at < cutoff, Alert.status.in_(["resolved", "closed"])))
        await db.execute(delete(AttackTimeline).where(AttackTimeline.created_at < cutoff))
        await db.execute(delete(CorrelationResult).where(CorrelationResult.detected_at < cutoff))
        if not settings.audit_immutable:
            audit_cutoff = datetime.now(timezone.utc) - timedelta(days=settings.audit_retention_days)
            await db.execute(delete(AuditLog).where(AuditLog.timestamp < audit_cutoff))
        await db.execute(delete(IngestDedup).where(IngestDedup.created_at < dedup_cutoff))
        await db.commit()
    if settings.event_partitioning_enabled:
        from app.services.event_partitions import drop_old_event_partitions, ensure_event_partitions

        await drop_old_event_partitions(cutoff)
        await ensure_event_partitions()
    logger.info("Retention completed: cutoff %s days", settings.retention_days)
