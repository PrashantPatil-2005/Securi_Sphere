#!/usr/bin/env python3
"""Backfill OpenSearch indices from PostgreSQL (bulk batches)."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.config import settings
from app.database import async_session
from app.models.alert import Alert
from app.models.event import Event
from app.models.host import Host
from app.search.bulk import chunk_iterable
from app.search.indexer import event_to_doc, index_alerts_batch, index_hosts_batch
from app.search.opensearch_client import bulk_index_event_docs


async def main(limit: int = 10_000) -> None:
    if not settings.opensearch_url:
        print("Set OPENSEARCH_URL in .env")
        return
    settings.search_backend = "opensearch"
    batch_size = settings.opensearch_bulk_size

    async with async_session() as db:
        hosts = list((await db.execute(select(Host))).scalars().all())
        host_map = {h.id: h.name for h in hosts}
        host_indexed = await index_hosts_batch(hosts)
        print(f"Indexed {host_indexed} hosts")

        events = list(
            (await db.execute(select(Event).order_by(Event.timestamp.desc()).limit(limit))).scalars().all()
        )
        event_docs = [event_to_doc(e, host_map.get(e.host_id, "?")) for e in events]
        events_indexed = 0
        for chunk in chunk_iterable(event_docs, batch_size):
            events_indexed += await bulk_index_event_docs(chunk)
        print(f"Indexed {events_indexed} events (from {len(events)} rows)")

        alerts = list(
            (
                await db.execute(select(Alert).order_by(Alert.created_at.desc()).limit(min(limit, 5000)))
            ).scalars().all()
        )
        alerts_indexed = await index_alerts_batch(alerts, host_map)
        print(f"Indexed {alerts_indexed} alerts (from {len(alerts)} rows)")

    print("Backfill complete")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10_000
    asyncio.run(main(n))
