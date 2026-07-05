"""Build OpenSearch Query DSL for SIEM-style field queries."""

from __future__ import annotations

from typing import Any, Literal

from app.utils.query import TimeRange


def _normalize_event_type(value: str) -> str:
    if value == "failed_login":
        return "ssh_login_failure"
    return value


def build_siem_index_query(
    parsed: dict,
    tr: TimeRange,
    *,
    index_kind: Literal["events", "alerts"],
    limit: int,
) -> dict[str, Any]:
    must: list[dict[str, Any]] = []
    ts_field = "created_at" if index_kind == "alerts" else "timestamp"

    if tr.from_time:
        must.append({"range": {ts_field: {"gte": tr.from_time.isoformat()}}})
    if tr.to_time:
        must.append({"range": {ts_field: {"lte": tr.to_time.isoformat()}}})

    filters = parsed["filters"]
    if "host" in filters:
        must.append(
            {
                "wildcard": {
                    "host_name": {"value": f"*{filters['host']}*", "case_insensitive": True},
                }
            }
        )
    if "severity" in filters:
        must.append({"term": {"severity": filters["severity"]}})

    if index_kind == "events":
        if "event_type" in filters:
            must.append({"term": {"event_type": _normalize_event_type(filters["event_type"])}})
        if "username" in filters:
            must.append(
                {
                    "wildcard": {
                        "username": {"value": f"*{filters['username']}*", "case_insensitive": True},
                    }
                }
            )
        if "source_ip" in filters:
            must.append({"term": {"source_ip": filters["source_ip"]}})
    elif "status" in filters:
        must.append({"term": {"status": filters["status"]}})

    if parsed["free_text"]:
        if index_kind == "alerts":
            must.append(
                {
                    "multi_match": {
                        "query": parsed["free_text"],
                        "fields": ["title", "description"],
                    }
                }
            )
        else:
            must.append(
                {
                    "multi_match": {
                        "query": parsed["free_text"],
                        "fields": ["description", "raw_log", "event_type", "host_name"],
                    }
                }
            )

    query = {"bool": {"must": must}} if must else {"match_all": {}}
    sort = [{"created_at": "desc"}] if index_kind == "alerts" else [{"timestamp": "desc"}]
    return {"query": query, "size": limit, "sort": sort}
