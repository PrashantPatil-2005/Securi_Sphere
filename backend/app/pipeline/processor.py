"""Post-ingestion processing: detection, correlation, offenses, scoring."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.host import Host
from app.services.correlation_engine import run_correlation_engine
from app.services.detection import check_service_failure_event, run_detection_for_host
from app.services.threat_score import calculate_host_scores
from app.services.timeline import build_timelines


async def run_post_ingestion_pipeline(db: AsyncSession, host_id: UUID) -> None:
    """Run expensive security processing outside the HTTP critical path when async."""
    host = await db.get(Host, host_id)
    if not host:
        return
    await run_detection_for_host(db, host)
    await run_correlation_engine(db, host_id)
    await build_timelines(db, host_id)
    await calculate_host_scores(db, host)
