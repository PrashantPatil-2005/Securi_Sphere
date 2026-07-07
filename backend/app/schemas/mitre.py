from datetime import datetime

from pydantic import BaseModel


class MitreDrilldownHost(BaseModel):
    host_id: str
    host_name: str
    event_count: int


class MitreDrilldownEvent(BaseModel):
    id: str
    host_id: str
    event_type: str
    severity: str
    description: str | None
    timestamp: datetime


class MitreDrilldownAlert(BaseModel):
    id: str
    host_id: str
    title: str
    severity: str
    status: str
    created_at: datetime


class MitreDrilldownResponse(BaseModel):
    technique_id: str
    tactic: str
    name: str
    description: str | None
    event_count: int
    alert_count: int
    top_hosts: list[MitreDrilldownHost]
    recent_events: list[MitreDrilldownEvent]
    recent_alerts: list[MitreDrilldownAlert]
