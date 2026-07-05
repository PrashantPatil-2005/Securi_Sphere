"""Layer 1 — network flow collection (QRadar Flow Collector equivalent).

Converts flow records (router/switch/agent summaries) into normalized security events.
"""

from __future__ import annotations

from datetime import datetime

from app.schemas.agent import EventIngest, FlowIngest


def flow_to_event(flow: FlowIngest) -> EventIngest:
    proto = flow.protocol.upper()
    src = f"{flow.src_ip}:{flow.src_port}" if flow.src_port else flow.src_ip
    dst = f"{flow.dst_ip}:{flow.dst_port}" if flow.dst_port else flow.dst_ip
    parts = [f"{proto} {src} → {dst}"]
    if flow.bytes_in or flow.bytes_out:
        parts.append(f"bytes {flow.bytes_in or 0}/{flow.bytes_out or 0}")
    if flow.packets:
        parts.append(f"pkts {flow.packets}")
    if flow.direction:
        parts.append(flow.direction)

    metadata = {
        "src_ip": flow.src_ip,
        "dst_ip": flow.dst_ip,
        "src_port": flow.src_port,
        "dst_port": flow.dst_port,
        "protocol": flow.protocol,
        "bytes_in": flow.bytes_in,
        "bytes_out": flow.bytes_out,
        "packets": flow.packets,
        "direction": flow.direction,
        "flow_source": flow.source,
    }

    return EventIngest(
        event_type="network_flow",
        severity=flow.severity,
        description=" · ".join(parts),
        source=flow.source or "flow-collector",
        raw_log=f"FLOW {proto} {flow.src_ip} {flow.dst_ip}",
        timestamp=flow.timestamp,
        metadata=metadata,
    )


def flows_to_events(flows: list[FlowIngest]) -> list[EventIngest]:
    return [flow_to_event(f) for f in flows]
