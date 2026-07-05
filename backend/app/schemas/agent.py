from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AgentRegisterRequest(BaseModel):
    enrollment_token: str
    hostname: str
    ip_address: str | None = None
    os_info: str | None = None
    agent_hash: str | None = None
    agent_version: str | None = None


class AgentRegisterResponse(BaseModel):
    api_key: str
    host_id: UUID


class EventIngest(BaseModel):
    event_type: str
    severity: str
    description: str | None = None
    source: str | None = None
    raw_log: str | None = None
    timestamp: datetime
    metadata: dict | None = None


class EventsBatch(BaseModel):
    events: list[EventIngest] = Field(max_length=100)


class MetricIngest(BaseModel):
    cpu_percent: float | None = None
    memory_percent: float | None = None
    disk_percent: float | None = None
    network_in: int | None = None
    network_out: int | None = None
    load_average: list[float] | None = None
    uptime_seconds: int | None = None
    recorded_at: datetime


class MetricsBatch(BaseModel):
    metrics: list[MetricIngest] = Field(max_length=100)


class FlowIngest(BaseModel):
    """NetFlow/sFlow-style record from router, switch, or host agent."""

    src_ip: str
    dst_ip: str
    src_port: int | None = None
    dst_port: int | None = None
    protocol: str = "tcp"
    bytes_in: int | None = None
    bytes_out: int | None = None
    packets: int | None = None
    direction: str | None = None
    severity: str = "info"
    source: str | None = None
    timestamp: datetime


class FlowsBatch(BaseModel):
    flows: list[FlowIngest] = Field(max_length=100)


class WindowsEventIngest(BaseModel):
    """Windows Event Log / Sysmon forwarder record."""

    event_id: str
    channel: str = "Security"
    message: str | None = None
    computer: str | None = None
    username: str | None = None
    source_ip: str | None = None
    provider: str | None = None
    severity: str = "medium"
    raw_log: str | None = None
    timestamp: datetime


class WindowsEventsBatch(BaseModel):
    events: list[WindowsEventIngest] = Field(max_length=100)
