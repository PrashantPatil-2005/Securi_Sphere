"""OpenSearch client helpers with Postgres fallback."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.core.circuit_guard import run_thread

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
        verify_certs=settings.opensearch_url.startswith("https"),
        ssl_show_warn=False,
    )
    return _client


def _ensure_ism_policy(client) -> None:
    from app.search.index_names import ISM_POLICY_ID
    from app.search.mappings import ism_retention_policy

    retention = settings.opensearch_retention_days or settings.retention_days
    body = ism_retention_policy(retention)
    path = f"/_plugins/_ism/policies/{ISM_POLICY_ID}"
    try:
        client.transport.perform_request("PUT", path, body=body)
    except Exception as exc:
        logger.debug("ISM policy setup skipped (plugin may be disabled): %s", exc)


def _ensure_indices(client) -> None:
    global _indices_ready
    if _indices_ready:
        return
    from app.search.index_names import EVENTS_INDEX_PREFIX, events_index_for
    from app.search.mappings import EVENTS_INDEX_TEMPLATE, INDEX_MAPPINGS

    try:
        client.indices.put_index_template(name="securi-events-template", body=EVENTS_INDEX_TEMPLATE)
    except Exception as exc:
        logger.debug("Index template setup: %s", exc)

    for index, body in INDEX_MAPPINGS.items():
        if not client.indices.exists(index=index):
            client.indices.create(index=index, body=body)

    current_month = events_index_for(datetime.now(timezone.utc))
    if not client.indices.exists(index=current_month):
        client.indices.create(index=current_month)

    _ensure_ism_policy(client)
    _indices_ready = True


def _resolve_events_index(doc: dict) -> str:
    from app.search.index_names import events_index_for, events_index_for_iso

    ts = doc.get("timestamp")
    if isinstance(ts, str):
        return events_index_for_iso(ts)
    if isinstance(ts, datetime):
        return events_index_for(ts)
    return events_index_for(datetime.now(timezone.utc))


def _bulk_index_sync(actions: list[dict[str, Any]]) -> int:
    if not actions:
        return 0
    client = _get_sync_client()
    if not client:
        return 0
    _ensure_indices(client)
    from opensearchpy.helpers import bulk

    success, _ = bulk(client, actions, refresh=False, raise_on_error=False)
    return success


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
        await run_thread("opensearch", lambda: _index_document(index, doc_id, body))
    except Exception as exc:
        logger.warning("OpenSearch index %s failed: %s", index, exc)


async def index_event_doc(doc: dict) -> None:
    index = _resolve_events_index(doc)
    await index_document(index, doc["id"], doc)


async def bulk_index_documents(index: str, docs: list[tuple[str, dict]]) -> int:
    """Bulk index documents. Returns count indexed."""
    if not opensearch_enabled() or not docs:
        return 0
    from app.search.bulk import build_bulk_actions, chunk_iterable

    indexed = 0
    batch_size = settings.opensearch_bulk_size

    def _run() -> int:
        total = 0
        for chunk in chunk_iterable(docs, batch_size):
            actions = build_bulk_actions(index, chunk)
            total += _bulk_index_sync(actions)
        return total

    try:
        indexed = await run_thread("opensearch", _run, fallback=0)
    except Exception as exc:
        logger.warning("OpenSearch bulk index failed: %s", exc)
        indexed = 0
    return indexed or 0


async def bulk_index_event_docs(docs: list[dict]) -> int:
    if not opensearch_enabled() or not docs:
        return 0
    from collections import defaultdict

    from app.search.bulk import build_bulk_actions, chunk_iterable

    by_index: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for doc in docs:
        by_index[_resolve_events_index(doc)].append((doc["id"], doc))

    batch_size = settings.opensearch_bulk_size

    def _run() -> int:
        total = 0
        for index, pairs in by_index.items():
            for chunk in chunk_iterable(pairs, batch_size):
                actions = build_bulk_actions(index, chunk)
                total += _bulk_index_sync(actions)
        return total

    try:
        result = await run_thread("opensearch", _run, fallback=0)
        return result or 0
    except Exception as exc:
        logger.warning("OpenSearch bulk event index failed: %s", exc)
        return 0


def _extract_total(hits: dict) -> int:
    total = hits.get("total")
    if isinstance(total, dict):
        return int(total.get("value", 0))
    if isinstance(total, int):
        return total
    return len(hits.get("hits", []))


async def opensearch_cluster_health() -> dict | None:
    if not settings.opensearch_url:
        return None

    def _health() -> dict:
        client = _get_sync_client()
        if not client:
            return {"status": "unconfigured"}
        try:
            cluster = client.cluster.health()
            stats = client.indices.stats(index="securi-*")
            indices_info = stats.get("indices", {}) or {}
            events_indices = sorted(k for k in indices_info if k.startswith("securi-events"))

            def _docs_for(prefix: str) -> int:
                total = 0
                for name, data in indices_info.items():
                    if name.startswith(prefix):
                        total += data.get("primaries", {}).get("docs", {}).get("count", 0)
                return total

            retention = settings.opensearch_retention_days or settings.retention_days
            return {
                "status": cluster.get("status", "unknown"),
                "number_of_nodes": cluster.get("number_of_nodes", 0),
                "active_shards": cluster.get("active_shards", 0),
                "indices": len(indices_info),
                "events_indices": len(events_indices),
                "events_docs": _docs_for("securi-events"),
                "alerts_docs": _docs_for("securi-alerts"),
                "hosts_docs": _docs_for("securi-hosts"),
                "oldest_event_index": events_indices[0] if events_indices else None,
                "ism_retention_days": retention,
            }
        except Exception as exc:
            return {"status": "error", "detail": str(exc)}

    try:
        return await run_thread("opensearch", _health, fallback=None)
    except Exception:
        return {"status": "error", "detail": "circuit or cluster failure"}


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

    from app.search.index_names import ALERTS_INDEX, EVENTS_SEARCH_PATTERN, HOSTS_INDEX

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
            index=EVENTS_SEARCH_PATTERN,
            body={
                "query": {"bool": {"must": must}},
                "size": limit,
                "sort": [{"timestamp": "desc"}],
                "track_total_hits": True,
            },
        )
        alerts_hits = client.search(
            index=ALERTS_INDEX,
            body={
                "query": {"multi_match": {"query": q, "fields": ["title", "description"]}},
                "size": limit,
                "track_total_hits": True,
            },
        )
        hosts_hits = client.search(
            index=HOSTS_INDEX,
            body={
                "query": {"multi_match": {"query": q, "fields": ["name", "hostname", "ip"]}},
                "size": limit,
                "track_total_hits": True,
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
        return await run_thread("opensearch", _search, fallback=None)
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

    from app.search.index_names import ALERTS_INDEX, EVENTS_SEARCH_PATTERN
    from app.search.siem_opensearch import build_siem_index_query

    def _search() -> dict:
        _ensure_indices(client)
        events_body = build_siem_index_query(parsed, tr, index_kind="events", limit=limit)
        events_body["track_total_hits"] = True
        alerts_body = build_siem_index_query(parsed, tr, index_kind="alerts", limit=limit)
        alerts_body["track_total_hits"] = True

        events_hits = client.search(index=EVENTS_SEARCH_PATTERN, body=events_body)
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
            "total_events": _extract_total(events_hits["hits"]),
            "total_alerts": _extract_total(alerts_hits["hits"]),
        }

    try:
        return await run_thread("opensearch", _search, fallback=None)
    except Exception as exc:
        logger.warning("OpenSearch SIEM search failed, caller should fallback: %s", exc)
        return None
