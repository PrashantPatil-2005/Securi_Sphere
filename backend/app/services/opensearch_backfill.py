"""OpenSearch backfill service — bulk reindex from PostgreSQL."""

from __future__ import annotations

import logging

from sqlalchemy import select

from app.config import settings
from app.database import async_session
from app.models.alert import Alert
from app.models.event import Event
from app.models.host import Host
from app.search.bulk import chunk_iterable
from app.search.indexer import event_to_doc, index_alerts_batch, index_hosts_batch
from app.search.opensearch_client import bulk_index_event_docs

logger = logging.getLogger(__name__)


async def run_opensearch_backfill(*, event_limit: int = 10_000, alert_limit: int = 5000) -> dict:
    """Bulk index hosts, events, and alerts. Returns counts."""
    if not settings.opensearch_url:
        raise ValueError("OPENSEARCH_URL is not configured")

    settings.search_backend = "opensearch"
    batch_size = settings.opensearch_bulk_size

    async with async_session() as db:
        hosts = list((await db.execute(select(Host))).scalars().all())
        host_map = {h.id: h.name for h in hosts}
        hosts_indexed = await index_hosts_batch(hosts)

        events = list(
            (await db.execute(select(Event).order_by(Event.timestamp.desc()).limit(event_limit))).scalars().all()
        )
        event_docs = [event_to_doc(e, host_map.get(e.host_id, "?")) for e in events]
        events_indexed = 0
        for chunk in chunk_iterable(event_docs, batch_size):
            events_indexed += await bulk_index_event_docs(chunk)

        alerts = list(
            (await db.execute(select(Alert).order_by(Alert.created_at.desc()).limit(alert_limit))).scalars().all()
        )
        alerts_indexed = await index_alerts_batch(alerts, host_map)

    result = {
        "hosts": hosts_indexed,
        "events": events_indexed,
        "alerts": alerts_indexed,
        "event_limit": event_limit,
        "alert_limit": alert_limit,
    }
    logger.info("OpenSearch backfill complete", extra=result)
    return result
