"""Job handlers for async background processing."""

import logging
from uuid import UUID

from app.database import async_session
from app.jobs.queue import job_queue
from app.services.notifications import notify_alert, notify_offense
from app.services.retention import run_retention
from app.services.threat_score import calculate_host_scores, update_all_threat_scores

logger = logging.getLogger(__name__)


async def handle_notify_alert(alert_id: str) -> None:
    from sqlalchemy import select
    from app.models.alert import Alert

    async with async_session() as db:
        alert = (await db.execute(select(Alert).where(Alert.id == UUID(alert_id)))).scalar_one_or_none()
        if alert:
            await notify_alert(db, alert)
            await db.commit()


async def handle_notify_offense(offense_id: str) -> None:
    from sqlalchemy import select
    from app.models.siem import Offense

    async with async_session() as db:
        offense = (await db.execute(select(Offense).where(Offense.id == UUID(offense_id)))).scalar_one_or_none()
        if offense:
            await notify_offense(db, offense)
            await db.commit()


async def handle_threat_score(host_id: str) -> None:
    from sqlalchemy import select
    from app.models.host import Host

    async with async_session() as db:
        host = (await db.execute(select(Host).where(Host.id == UUID(host_id)))).scalar_one_or_none()
        if host:
            await calculate_host_scores(db, host)
            await db.commit()


async def handle_threat_score_all() -> None:
    async with async_session() as db:
        await update_all_threat_scores(db)
        await db.commit()


async def handle_retention() -> None:
    await run_retention()


async def handle_correlation_pipeline(host_id: str) -> None:
    from uuid import UUID as UUIDType
    from app.pipeline.processor import run_post_ingestion_pipeline

    async with async_session() as db:
        await run_post_ingestion_pipeline(db, UUIDType(host_id))
        await db.commit()


def register_job_handlers() -> None:
    job_queue.register("notify_alert", handle_notify_alert)
    job_queue.register("notify_offense", handle_notify_offense)
    job_queue.register("threat_score", handle_threat_score)
    job_queue.register("threat_score_all", handle_threat_score_all)
    job_queue.register("retention", handle_retention)
    job_queue.register("correlation_pipeline", handle_correlation_pipeline)
