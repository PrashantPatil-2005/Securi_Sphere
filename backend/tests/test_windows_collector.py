"""Tests for Windows event forwarder (Layer 1 spike)."""

from datetime import datetime, timezone

from app.pipeline.windows_collector import windows_event_to_ingest, windows_events_to_ingest
from app.schemas.agent import WindowsEventIngest


def test_windows_login_failure_maps_to_high_severity():
    item = WindowsEventIngest(
        event_id="4625",
        channel="Security",
        message="An account failed to log on",
        computer="WIN-DC01",
        username="admin",
        source_ip="203.0.113.10",
        provider="Microsoft-Windows-Security-Auditing",
        timestamp=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
    )
    event = windows_event_to_ingest(item)
    assert event.event_type == "ssh_login_failure"
    assert event.severity == "high"
    assert event.metadata["windows_event_id"] == "4625"
    assert event.metadata["computer"] == "WIN-DC01"
    assert event.source == "Microsoft-Windows-Security-Auditing"


def test_unknown_event_id_gets_prefixed_type():
    item = WindowsEventIngest(
        event_id="9999",
        channel="Application",
        timestamp=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
    )
    event = windows_event_to_ingest(item)
    assert event.event_type == "win_event_9999"
    assert event.severity == "medium"


def test_windows_events_batch():
    items = [
        WindowsEventIngest(event_id="1", channel="Microsoft-Windows-Sysmon", timestamp=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)),
        WindowsEventIngest(event_id="3", channel="Microsoft-Windows-Sysmon", timestamp=datetime(2026, 1, 15, 12, 1, tzinfo=timezone.utc)),
    ]
    events = windows_events_to_ingest(items)
    assert len(events) == 2
    assert events[0].event_type == "process_start"
    assert events[1].event_type == "network_connection"
