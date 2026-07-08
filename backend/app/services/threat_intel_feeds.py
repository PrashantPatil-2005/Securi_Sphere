"""Threat intel feed ingestion for reference sets."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.http_timeouts import outbound_timeout
from app.models.reference import ReferenceSet, ReferenceSetEntry

VALID_FEED_FORMATS = frozenset({"txt", "csv", "json"})


def _infer_feed_format(url: str, explicit: str | None) -> str:
    if explicit in VALID_FEED_FORMATS:
        return explicit
    path = urlparse(url).path.lower()
    if path.endswith(".csv"):
        return "csv"
    if path.endswith(".json"):
        return "json"
    return "txt"


def _normalize_values(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in values:
        value = (raw or "").strip()
        if not value or value.startswith("#"):
            continue
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def parse_feed_values(payload: str, feed_format: str) -> list[str]:
    fmt = feed_format.lower()
    if fmt == "txt":
        return _normalize_values(payload.splitlines())

    if fmt == "csv":
        reader = csv.reader(io.StringIO(payload))
        vals = [row[0] for row in reader if row and row[0]]
        if vals and vals[0].strip().lower() in {"value", "indicator", "ioc"}:
            vals = vals[1:]
        return _normalize_values(vals)

    if fmt == "json":
        data = json.loads(payload)
        vals: list[str] = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    vals.append(item)
                elif isinstance(item, dict):
                    for key in ("value", "indicator", "ioc", "ip", "domain", "hash"):
                        if key in item and item[key]:
                            vals.append(str(item[key]))
                            break
        return _normalize_values(vals)

    raise ValueError(f"Unsupported feed format: {feed_format}")


async def fetch_remote_feed(url: str) -> str:
    async with httpx.AsyncClient(timeout=outbound_timeout()) as client:
        res = await client.get(url)
        res.raise_for_status()
        return res.text


async def sync_reference_set_feed(db: AsyncSession, reference_set: ReferenceSet) -> dict:
    if reference_set.source_type != "feed":
        raise ValueError("Reference set is not feed-backed")
    if not reference_set.feed_url:
        raise ValueError("Feed URL is not configured")

    feed_format = _infer_feed_format(reference_set.feed_url, reference_set.feed_format)
    payload = await fetch_remote_feed(reference_set.feed_url)
    values = parse_feed_values(payload, feed_format)

    existing = set(
        (
            await db.execute(
                select(ReferenceSetEntry.value).where(ReferenceSetEntry.set_id == reference_set.id)
            )
        ).scalars().all()
    )
    added = 0
    for value in values:
        if value in existing:
            continue
        db.add(ReferenceSetEntry(set_id=reference_set.id, value=value, note="feed_sync"))
        existing.add(value)
        added += 1

    reference_set.feed_format = feed_format
    reference_set.feed_last_sync_at = datetime.now(timezone.utc)
    reference_set.feed_last_sync_status = "ok"
    reference_set.feed_last_sync_error = None
    await db.flush()
    return {"added": added, "total_parsed": len(values), "feed_format": feed_format}


async def sync_all_enabled_feeds(db: AsyncSession) -> dict:
    sets = list(
        (
            await db.execute(
                select(ReferenceSet).where(
                    ReferenceSet.enabled.is_(True),
                    ReferenceSet.source_type == "feed",
                    ReferenceSet.feed_url.isnot(None),
                )
            )
        ).scalars().all()
    )
    synced = 0
    failed = 0
    for rs in sets:
        try:
            await sync_reference_set_feed(db, rs)
            synced += 1
        except Exception as exc:
            rs.feed_last_sync_at = datetime.now(timezone.utc)
            rs.feed_last_sync_status = "error"
            rs.feed_last_sync_error = str(exc)[:255]
            failed += 1
    await db.flush()
    return {"synced": synced, "failed": failed, "total": len(sets)}
