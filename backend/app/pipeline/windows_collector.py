"""Layer 1 — Windows Event Log forwarder (spike).

Maps Windows/Sysmon-style records into normalized Linux SIEM events.
"""

from __future__ import annotations

from app.schemas.agent import EventIngest, WindowsEventIngest

WIN_EVENT_MAP = {
    "4625": "ssh_login_failure",
    "4624": "ssh_login_success",
    "4688": "process_start",
    "4698": "service_failure",
    "7045": "service_failure",
    "1": "process_start",
    "3": "network_connection",
    "11": "file_change",
}


def windows_event_to_ingest(item: WindowsEventIngest) -> EventIngest:
    event_type = WIN_EVENT_MAP.get(item.event_id, f"win_event_{item.event_id}")
    severity = item.severity
    if event_type in ("ssh_login_failure", "service_failure"):
        severity = "high"
    description = item.message or f"Windows {item.channel} {item.event_id}"
    metadata = {
        "windows_event_id": item.event_id,
        "channel": item.channel,
        "computer": item.computer,
        "username": item.username,
        "source_ip": item.source_ip,
        "provider": item.provider,
    }
    return EventIngest(
        event_type=event_type,
        severity=severity,
        description=description,
        source=item.provider or "windows-forwarder",
        raw_log=item.raw_log or description,
        timestamp=item.timestamp,
        metadata={k: v for k, v in metadata.items() if v},
    )


def windows_events_to_ingest(items: list[WindowsEventIngest]) -> list[EventIngest]:
    return [windows_event_to_ingest(i) for i in items]
