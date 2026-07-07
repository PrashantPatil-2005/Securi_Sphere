"""OpenSearch index naming — monthly rollover for high-volume events."""

from __future__ import annotations

from datetime import datetime

EVENTS_INDEX_PREFIX = "securi-events-"
EVENTS_SEARCH_PATTERN = "securi-events*"
ALERTS_INDEX = "securi-alerts"
HOSTS_INDEX = "securi-hosts"
ISM_POLICY_ID = "securi-events-retention"


def events_index_for(timestamp: datetime) -> str:
    return f"{EVENTS_INDEX_PREFIX}{timestamp.strftime('%Y.%m')}"


def events_index_for_iso(timestamp_iso: str) -> str:
    ts = datetime.fromisoformat(timestamp_iso.replace("Z", "+00:00"))
    return events_index_for(ts)
