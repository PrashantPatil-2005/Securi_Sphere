"""Job handlers for async background processing."""

import logging
from uuid import UUID

from app.database import async_session
from app.jobs.queue import job_queue
from app.services.notifications import notify_alert, notify_offense
from app.services.playbooks import dispatch_playbook_event
from app.services.ueba import scan_ueba_anomalies

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


async def handle_correlation_pipeline(host_id: str) -> None:
    from uuid import UUID as UUIDType
    from app.pipeline.processor import run_post_ingestion_pipeline

    async with async_session() as db:
        await run_post_ingestion_pipeline(db, UUIDType(host_id))
        await db.commit()


async def handle_playbook_dispatch(
    event: str,
    resource_type: str,
    resource_id: str,
    **extra,
) -> None:
    async with async_session() as db:
        await dispatch_playbook_event(db, event, resource_type, resource_id, **extra)
        await db.commit()


async def handle_ueba_scan() -> None:
    async with async_session() as db:
        await scan_ueba_anomalies(db)
        await db.commit()


async def handle_detection_and_scores(host_id: str) -> None:
    from uuid import UUID as UUIDType
    from app.services.detection import run_detection_for_host
    from app.services.threat_score import calculate_host_scores
    from app.models.host import Host

    async with async_session() as db:
        host = await db.get(Host, UUIDType(host_id))
        if host:
            await run_detection_for_host(db, host)
            await calculate_host_scores(db, host)
            await db.commit()


def register_job_handlers() -> None:
    job_queue.register("notify_alert", handle_notify_alert)
    job_queue.register("notify_offense", handle_notify_offense)
    job_queue.register("playbook_dispatch", handle_playbook_dispatch)
    job_queue.register("correlation_pipeline", handle_correlation_pipeline)
    job_queue.register("detection_and_scores", handle_detection_and_scores)
