import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete

from app.config import settings
from app.database import async_session
from app.models.event import Event
from app.models.metric import Metric

logger = logging.getLogger(__name__)


async def run_retention() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.retention_days)
    async with async_session() as db:
        await db.execute(delete(Event).where(Event.timestamp < cutoff))
        await db.execute(delete(Metric).where(Metric.recorded_at < cutoff))
        await db.commit()
    logger.info("Retention job completed: deleted data older than %s days", settings.retention_days)
