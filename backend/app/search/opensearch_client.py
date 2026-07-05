"""OpenSearch client helpers with Postgres fallback."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

_client = None
_indices_ready = False


def opensearch_enabled() -> bool:
    return bool(settings.opensearch_url) and settings.search_backend == "opensearch"


def _get_sync_client():
    global _client
    if _client is not None:
        return _client
    if not settings.opensearch_url:
        return None
    from opensearchpy import OpenSearch

    _client = OpenSearch(
        hosts=[settings.opensearch_url],
        use_ssl=settings.opensearch_url.startswith("https"),
        verify_certs=False,
        ssl_show_warn=False,
    )
    return _client


def _ensure_indices(client) -> None:
    global _indices_ready
    if _indices_ready:
        return
    from app.search.mappings import INDEX_MAPPINGS

    for index, body in INDEX_MAPPINGS.items():
        if not client.indices.exists(index=index):
            client.indices.create(index=index, body=body)
    _indices_ready = True


def _index_document(index: str, doc_id: str, body: dict) -> None:
    client = _get_sync_client()
    if not client:
        return
    _ensure_indices(client)
    client.index(index=index, id=doc_id, body=body, refresh=False)


async def index_document(index: str, doc_id: str, body: dict) -> None:
    if not opensearch_enabled():
        return
    try:
        await asyncio.to_thread(_index_document, index, doc_id, body)
    except Exception as exc:
        logger.warning("OpenSearch index %s failed: %s", index, exc)


async def index_event_doc(doc: dict) -> None:
    await index_document("securi-events", doc["id"], doc)


async def global_search_opensearch(
    q: str,
    *,
    exact: bool = False,
    from_time: str | None = None,
    to_time: str | None = None,
    limit: int = 20,
) -> dict[str, list[dict]] | None:
    if not opensearch_enabled():
        return None

    client = _get_sync_client()
    if not client:
        return None

    def _search() -> dict[str, list[dict]]:
        _ensure_indices(client)
        must: list[dict[str, Any]] = []
        if exact:
            must.append(
                {
                    "bool": {
                        "should": [
                            {"term": {"description.keyword": q}},
                            {"term": {"event_type": q}},
                            {"term": {"raw_log.keyword": q}},
                        ],
                        "minimum_should_match": 1,
                    }
                }
            )
        else:
            must.append(
                {
                    "multi_match": {
                        "query": q,
                        "fields": ["description", "event_type", "raw_log", "host_name"],
                    }
                }
            )
        if from_time or to_time:
            range_filter: dict[str, str] = {}
            if from_time:
                range_filter["gte"] = from_time
            if to_time:
                range_filter["lte"] = to_time
            must.append({"range": {"timestamp": range_filter}})

        events_hits = client.search(
            index="securi-events",
            body={"query": {"bool": {"must": must}}, "size": limit, "sort": [{"timestamp": "desc"}]},
        )
        alerts_hits = client.search(
            index="securi-alerts",
            body={
                "query": {
                    "multi_match": {
                        "query": q,
                        "fields": ["title", "description"],
                    }
                },
                "size": limit,
            },
        )
        hosts_hits = client.search(
            index="securi-hosts",
            body={
                "query": {
                    "multi_match": {
                        "query": q,
                        "fields": ["name", "hostname", "ip"],
                    }
                },
                "size": limit,
            },
        )

        events = [
            {
                "id": h["_source"]["id"],
                "event_type": h["_source"].get("event_type"),
                "description": h["_source"].get("description"),
                "severity": h["_source"].get("severity"),
            }
            for h in events_hits["hits"]["hits"]
        ]
        alerts = [
            {
                "id": h["_source"]["id"],
                "title": h["_source"].get("title"),
                "severity": h["_source"].get("severity"),
                "status": h["_source"].get("status"),
            }
            for h in alerts_hits["hits"]["hits"]
        ]
        hosts = [
            {
                "id": h["_source"]["id"],
                "name": h["_source"].get("name"),
                "hostname": h["_source"].get("hostname"),
                "status": h["_source"].get("status"),
                "ip": h["_source"].get("ip"),
            }
            for h in hosts_hits["hits"]["hits"]
        ]
        return {"events": events, "alerts": alerts, "hosts": hosts}

    try:
        return await asyncio.to_thread(_search)
    except Exception as exc:
        logger.warning("OpenSearch search failed, caller should fallback: %s", exc)
        return None


async def siem_search_opensearch(
    parsed: dict,
    tr,
    *,
    limit: int = 50,
) -> dict | None:
    if not opensearch_enabled():
        return None

    client = _get_sync_client()
    if not client:
        return None

    from app.search.mappings import ALERTS_INDEX, EVENTS_INDEX
    from app.search.siem_opensearch import build_siem_index_query

    def _search() -> dict:
        _ensure_indices(client)
        events_body = build_siem_index_query(parsed, tr, index_kind="events", limit=limit)
        alerts_body = build_siem_index_query(parsed, tr, index_kind="alerts", limit=limit)

        events_hits = client.search(index=EVENTS_INDEX, body=events_body)
        alerts_hits = client.search(index=ALERTS_INDEX, body=alerts_body)

        events = [
            {
                "id": h["_source"]["id"],
                "event_type": h["_source"].get("event_type"),
                "severity": h["_source"].get("severity"),
                "description": h["_source"].get("description"),
                "timestamp": h["_source"].get("timestamp"),
                "host_id": h["_source"].get("host_id"),
            }
            for h in events_hits["hits"]["hits"]
        ]
        alerts = [
            {
                "id": h["_source"]["id"],
                "title": h["_source"].get("title"),
                "severity": h["_source"].get("severity"),
                "status": h["_source"].get("status"),
                "created_at": h["_source"].get("created_at"),
            }
            for h in alerts_hits["hits"]["hits"]
        ]
        return {
            "events": events,
            "alerts": alerts,
            "total_events": len(events),
            "total_alerts": len(alerts),
        }

    try:
        return await asyncio.to_thread(_search)
    except Exception as exc:
        logger.warning("OpenSearch SIEM search failed, caller should fallback: %s", exc)
        return None
