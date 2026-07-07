"""Run saved searches on a schedule and create alerts when matches are found."""

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.siem import SavedSearch
from app.services.detection import create_alert
from app.services.siem_search import execute_siem_search

logger = logging.getLogger(__name__)


async def _recent_alert_exists(db: AsyncSession, title: str, minutes: int) -> bool:
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    row = (
        await db.execute(
            select(Alert.id).where(Alert.title == title, Alert.created_at >= since).limit(1)
        )
    ).scalar_one_or_none()
    return row is not None


async def run_saved_search_alerts(db: AsyncSession) -> int:
    """Evaluate saved searches with alert_enabled; returns alerts created."""
    rows = (
        await db.execute(select(SavedSearch).where(SavedSearch.alert_enabled.is_(True)))
    ).scalars().all()
    created = 0
    now = datetime.now(timezone.utc)
    for search in rows:
        q = search.query.strip()
        if not q:
            continue
        title = f"Saved search match: {search.name}"
        if await _recent_alert_exists(db, title, search.interval_minutes):
            continue
        window = max(search.interval_minutes, 5)
        result = await execute_siem_search(
            db,
            q,
            from_time=now - timedelta(minutes=window),
            to_time=now,
            limit=1,
        )
        if result["total_events"] == 0 and result["total_alerts"] == 0:
            continue
        host_id = None
        if result["events"]:
            host_id = UUID(result["events"][0]["host_id"])
        elif result["alerts"]:
            alert_row = (
                await db.execute(select(Alert).where(Alert.id == result["alerts"][0]["id"]).limit(1))
            ).scalar_one_or_none()
            if alert_row:
                host_id = alert_row.host_id
        if not host_id:
            continue
        total = result["total_events"] + result["total_alerts"]
        alert = await create_alert(
            db,
            host_id,
            title,
            f"Query '{q}' matched {total} result(s) in the last {window} minutes.",
            "medium",
            None,
        )
        if alert:
            created += 1
    return created
