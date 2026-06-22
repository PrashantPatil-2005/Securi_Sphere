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
