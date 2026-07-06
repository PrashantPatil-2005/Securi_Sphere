#!/usr/bin/env python3
"""Backfill OpenSearch indices from PostgreSQL (spike / dev tool)."""

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
from app.search.indexer import index_alert, index_event, index_host


async def main(limit: int = 10_000) -> None:
    if not settings.opensearch_url:
        print("Set OPENSEARCH_URL in .env")
        return
    settings.search_backend = "opensearch"

    async with async_session() as db:
        hosts = {h.id: h for h in (await db.execute(select(Host))).scalars().all()}
        for host in hosts.values():
            await index_host(host)

        events = list((await db.execute(select(Event).order_by(Event.timestamp.desc()).limit(limit))).scalars().all())
        for event in events:
            host = hosts.get(event.host_id)
            await index_event(event, host.name if host else "?")

        alerts = list((await db.execute(select(Alert).order_by(Alert.created_at.desc()).limit(min(limit, 5000)))).scalars().all())
        for alert in alerts:
            host = hosts.get(alert.host_id)
            await index_alert(alert, host.name if host else "")

    print(f"Indexed {len(hosts)} hosts, {len(events)} events, {len(alerts)} alerts")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10_000
    asyncio.run(main(n))
