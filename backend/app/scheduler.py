"""Background job scheduler — all APScheduler jobs live here."""

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.database import async_session
from app.jobs.handlers import register_job_handlers
from app.services.analytics.aggregator import aggregate_daily_stats
from app.services.backup import run_scheduled_backup
from app.services.correlation_engine import run_cross_host_correlation
from app.services.detection import update_host_statuses
from app.services.retention import run_retention
from app.services.saved_search_alerts import run_saved_search_alerts
from app.services.threat_score import update_all_threat_scores
from app.services.ueba import scan_ueba_anomalies

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def saved_search_job() -> None:
    try:
        async with async_session() as db:
            await run_saved_search_alerts(db)
            await db.commit()
    except Exception:
        logger.error("saved_search_job failed", exc_info=True)


async def status_job() -> None:
    try:
        async with async_session() as db:
            await update_host_statuses(db)
            await update_all_threat_scores(db)
            await db.commit()
    except Exception:
        logger.error("status_job failed", exc_info=True)


async def analytics_job() -> None:
    try:
        async with async_session() as db:
            await aggregate_daily_stats(db)
            await db.commit()
    except Exception:
        logger.error("analytics_job failed", exc_info=True)


async def analytics_mv_job() -> None:
    if not settings.analytics_materialized_views_enabled:
        return
    from app.services.analytics.materialized_views import refresh_analytics_materialized_views
    try:
        async with async_session() as db:
            await refresh_analytics_materialized_views(db)
            await db.commit()
    except Exception:
        logger.error("analytics_mv_job failed", exc_info=True)


async def cross_host_correlation_job() -> None:
    try:
        async with async_session() as db:
            await run_cross_host_correlation(db)
            await db.commit()
    except Exception:
        logger.error("cross_host_correlation_job failed", exc_info=True)


async def ueba_scan_job() -> None:
    try:
        async with async_session() as db:
            await scan_ueba_anomalies(db)
            await db.commit()
    except Exception:
        logger.error("ueba_scan_job failed", exc_info=True)


async def backup_job() -> None:
    try:
        await run_scheduled_backup()
    except Exception:
        logger.error("backup_job failed", exc_info=True)


async def threat_intel_feed_job() -> None:
    if not settings.threat_intel_feeds_enabled:
        return
    from app.services.threat_intel_feeds import sync_all_enabled_feeds
    try:
        async with async_session() as db:
            await sync_all_enabled_feeds(db)
            await db.commit()
    except Exception:
        logger.error("threat_intel_feed_job failed", exc_info=True)


def start_scheduler() -> None:
    """Register all jobs and start the scheduler.

    All jobs use max_instances=1 to prevent overlapping runs.
    coalesce=True: if a job misses multiple triggers, only one run is executed.
    misfire_grace_time=60: jobs triggered within 60s of their schedule are still run.
    """
    register_job_handlers()
    now = datetime.now()
    scheduler.add_job(status_job, "interval", seconds=30, id="host_status",
                      next_run_time=now + timedelta(seconds=30), max_instances=1,
                      coalesce=True, misfire_grace_time=60)
    scheduler.add_job(
        cross_host_correlation_job,
        "interval",
        seconds=settings.cross_host_correlation_interval_seconds,
        id="cross_host_correlation",
        next_run_time=now + timedelta(seconds=60),
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60,
    )
    scheduler.add_job(run_retention, "cron", hour=2, id="retention",
                      next_run_time=now + timedelta(hours=1), max_instances=1,
                      coalesce=True, misfire_grace_time=3600)
    scheduler.add_job(backup_job, "cron", hour=settings.backup_schedule_hour, id="postgres_backup",
                      next_run_time=now + timedelta(hours=1), max_instances=1,
                      coalesce=True, misfire_grace_time=3600)
    scheduler.add_job(analytics_job, "cron", hour=3, id="analytics",
                      next_run_time=now + timedelta(hours=1), max_instances=1,
                      coalesce=True, misfire_grace_time=3600)
    scheduler.add_job(
        analytics_mv_job,
        "interval",
        minutes=settings.analytics_mv_refresh_interval_minutes,
        id="analytics_materialized_views",
        next_run_time=now + timedelta(minutes=5),
        max_instances=1,
        coalesce=True,
        misfire_grace_time=120,
    )
    scheduler.add_job(
        threat_intel_feed_job,
        "interval",
        minutes=settings.threat_intel_feed_sync_minutes,
        id="threat_intel_feed_sync",
        next_run_time=now + timedelta(minutes=3),
        max_instances=1,
        coalesce=True,
        misfire_grace_time=120,
    )
    scheduler.add_job(ueba_scan_job, "interval", minutes=settings.ueba_scan_interval_minutes, id="ueba_scan",
                      next_run_time=now + timedelta(minutes=2), max_instances=1,
                      coalesce=True, misfire_grace_time=120)
    scheduler.add_job(saved_search_job, "interval", minutes=5, id="saved_search_alerts",
                      next_run_time=now + timedelta(minutes=1), max_instances=1,
                      coalesce=True, misfire_grace_time=120)
    scheduler.start()
    logger.info("Scheduler started")
