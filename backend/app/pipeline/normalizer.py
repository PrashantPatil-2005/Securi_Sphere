"""Canonical event normalization — every event gets a structured normalized form."""

from datetime import datetime
from typing import Any
from uuid import UUID

EVENT_CATEGORIES: dict[str, str] = {
    "ssh_login_failure": "authentication",
    "ssh_login_success": "authentication",
    "root_login": "authentication",
    "sudo_usage": "privilege",
    "service_failure": "system",
    "service_stop": "system",
    "agent_disconnect": "agent",
    "file_change": "integrity",
    "network_connection": "network",
    "process_start": "execution",
    "firewall_block": "network",
}

SEVERITY_ALIASES = {
    "failed_login": "ssh_login_failure",
    "login_failure": "ssh_login_failure",
    "login_success": "ssh_login_success",
    "auth_failure": "ssh_login_failure",
}


def normalize_event_type(event_type: str) -> str:
    return SEVERITY_ALIASES.get(event_type.lower(), event_type.lower())


def categorize_event(event_type: str) -> str:
    return EVENT_CATEGORIES.get(event_type, "general")


def extract_field(metadata: dict | None, *keys: str) -> str | None:
    if not metadata:
        return None
    for key in keys:
        val = metadata.get(key)
        if val is not None:
            return str(val)
    return None


def build_normalized_event(
    *,
    event_id: UUID | None,
    timestamp: datetime,
    host_id: UUID,
    event_type: str,
    severity: str,
    description: str | None,
    source: str | None,
    raw_log: str | None,
    metadata: dict | None,
) -> dict[str, Any]:
    normalized_type = normalize_event_type(event_type)
    username = extract_field(metadata, "username", "user", "account")
    source_ip = extract_field(metadata, "source_ip", "src_ip", "ip", "remote_addr")
    category = categorize_event(normalized_type)

    normalized = {
        "id": str(event_id) if event_id else None,
        "timestamp": timestamp.isoformat(),
        "host_id": str(host_id),
        "source_ip": source_ip,
        "username": username,
        "event_type": normalized_type,
        "severity": severity,
        "category": category,
        "source": source,
        "description": description,
        "raw_event": raw_log,
        "tags": [],
        "fields": metadata or {},
    }

    if normalized_type in ("ssh_login_failure", "ssh_login_success", "sudo_usage", "root_login"):
        normalized["tags"].append("auth")
    if severity in ("high", "critical"):
        normalized["tags"].append("security")

    return normalized
