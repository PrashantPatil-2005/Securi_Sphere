"""Run saved searches on a schedule and create alerts when matches are found."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.siem import SavedSearch
from app.services.detection import create_alert

logger = logging.getLogger(__name__)


async def run_saved_search_alerts(db: AsyncSession) -> int:
    """Evaluate saved searches with alert_enabled; returns alerts created."""
    rows = (
        await db.execute(
            select(SavedSearch).where(SavedSearch.alert_enabled.is_(True))
        )
    ).scalars().all()
    created = 0
    since = datetime.now(timezone.utc) - timedelta(minutes=5)
    for search in rows:
        q = search.query.strip()
        if not q:
            continue
        events = (
            await db.execute(
                select(Event)
                .where(
                    Event.timestamp >= since,
                    or_(
                        Event.event_type.ilike(f"%{q}%"),
                        Event.description.ilike(f"%{q}%"),
                    ),
                )
                .limit(1)
            )
        ).scalars().all()
        if not events:
            continue
        ev = events[0]
        alert = await create_alert(
            db,
            ev.host_id,
            f"Saved search match: {search.name}",
            f"Query '{q}' matched event {ev.event_type}",
            "medium",
            None,
        )
        if alert:
            created += 1
    return created
