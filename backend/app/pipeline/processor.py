"""Post-ingestion processing: detection, correlation, offenses, scoring."""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.host import Host

logger = logging.getLogger(__name__)


async def run_post_ingestion_pipeline(db: AsyncSession, host_id: UUID) -> None:
    """Run expensive security processing outside the HTTP critical path when async.

    Each stage is independently isolated so that a failure in one stage
    (e.g., detection) does not prevent subsequent stages from running,
    and critically does not roll back the already-committed event ingestion.
    """
    host = await db.get(Host, host_id)
    if not host:
        return

    from app.services.detection import run_detection_for_host
    from app.services.correlation_engine import run_correlation_engine
    from app.services.timeline import build_timelines
    from app.services.threat_score import calculate_host_scores

    stages = [
        ("detection", lambda: run_detection_for_host(db, host)),
        ("correlation", lambda: run_correlation_engine(db, host_id)),
        ("timeline", lambda: build_timelines(db, host_id)),
        ("threat_score", lambda: calculate_host_scores(db, host)),
    ]

    for stage_name, stage_fn in stages:
        try:
            await stage_fn()
        except Exception:
            logger.exception(
                "post-ingestion stage '%s' failed for host %s",
                stage_name,
                host_id,
            )
