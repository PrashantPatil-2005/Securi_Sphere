"""Coerce agent event payloads into EventIngest models without failing the batch.

v3.0.0 agents send individual event dicts. Older buffers and a metrics-buffering
bug can mix in non-event objects. Pydantic all-or-nothing validation of the
batch used to raise inside the route handler and become HTTP 500.
"""

from __future__ import annotations

import ipaddress
import json
import re
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from app.pipeline.validator import MAX_BATCH_SIZE
from app.schemas.agent import EventIngest

_IPV4_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
)
_SOURCE_MAX = 50


def safe_inet(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        ipaddress.ip_address(text)
    except ValueError:
        return None
    return text


def _strip_nuls(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace("\x00", "")
    return value


def _looks_like_metric(item: dict) -> bool:
    return "event_type" not in item and (
        "cpu_percent" in item or "memory_percent" in item or "recorded_at" in item
    )


def flatten_event_items(items: list[Any]) -> list[Any]:
    """Unwrap accidental {\"events\": [...]} objects nested in the batch."""
    out: list[Any] = []
    for item in items:
        if (
            isinstance(item, dict)
            and "event_type" not in item
            and isinstance(item.get("events"), list)
        ):
            out.extend(flatten_event_items(item["events"]))
        else:
            out.append(item)
    return out


def sanitize_event_dict(raw: dict) -> dict:
    data = dict(raw)
    for key in ("description", "raw_log", "source", "event_type", "severity"):
        if key in data:
            data[key] = _strip_nuls(data[key])
    source = data.get("source")
    if isinstance(source, str) and len(source) > _SOURCE_MAX:
        data["source"] = source[:_SOURCE_MAX]
    metadata = data.get("metadata")
    if isinstance(metadata, dict):
        cleaned = dict(metadata)
        for ip_key in ("source_ip", "src_ip", "ip", "remote_addr"):
            if ip_key in cleaned:
                cleaned[ip_key] = safe_inet(cleaned[ip_key])
        data["metadata"] = cleaned
    return data


def ip_from_raw_log(raw_log: str | None) -> str | None:
    if not raw_log:
        return None
    match = _IPV4_RE.search(raw_log)
    if not match:
        return None
    return safe_inet(match.group(0))


def coerce_event_ingests(items: list[Any]) -> tuple[list[EventIngest], list[str]]:
    events: list[EventIngest] = []
    errors: list[str] = []
    flattened = flatten_event_items(items)
    for idx, item in enumerate(flattened):
        if not isinstance(item, dict):
            errors.append(f"event[{idx}]: expected object, got {type(item).__name__}")
            continue
        if _looks_like_metric(item):
            errors.append(f"event[{idx}]: metric payload sent to events endpoint — skipped")
            continue
        try:
            events.append(EventIngest.model_validate(sanitize_event_dict(item)))
        except PydanticValidationError as exc:
            loc = exc.errors()[0].get("loc", ()) if exc.errors() else ()
            msg = exc.errors()[0].get("msg", "invalid event") if exc.errors() else "invalid event"
            errors.append(f"event[{idx}]: {'.'.join(str(p) for p in loc)} {msg}".strip())
    return events, errors


def parse_events_body(raw_body: bytes) -> tuple[list[Any] | None, str | None]:
    """Return (items, error). error is set when the HTTP body itself is invalid."""
    if not raw_body:
        return None, "Request body is required"
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return None, "Invalid JSON"
    if not isinstance(payload, dict):
        return None, "Body must be a JSON object"
    if "events" not in payload:
        return None, "Body must contain an 'events' array"
    items = payload["events"]
    if not isinstance(items, list):
        return None, "events must be an array"
    if len(items) > MAX_BATCH_SIZE:
        return None, f"batch exceeds max size of {MAX_BATCH_SIZE}"
    return items, None
