"""Tests for flow collector (Layer 1)."""

from datetime import datetime, timezone

from app.pipeline.flow_collector import flow_to_event
from app.schemas.agent import FlowIngest


def test_flow_to_event_normalization():
    flow = FlowIngest(
        src_ip="10.0.0.5",
        dst_ip="8.8.8.8",
        src_port=44321,
        dst_port=443,
        protocol="tcp",
        bytes_in=1200,
        bytes_out=4096,
        packets=12,
        direction="outbound",
        timestamp=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
    )
    event = flow_to_event(flow)
    assert event.event_type == "network_flow"
    assert event.metadata["src_ip"] == "10.0.0.5"
    assert event.metadata["dst_ip"] == "8.8.8.8"
    assert "10.0.0.5:44321" in event.description
    assert event.source == "flow-collector"
