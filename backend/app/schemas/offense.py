"""Offense schemas."""

from pydantic import BaseModel, Field


VALID_OFFENSE_STATUSES = ("open", "investigating", "resolved")


class OffenseStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(open|investigating|resolved)$")


class OffenseEventRef(BaseModel):
    id: str
    event_type: str
    description: str | None = None
    severity: str
    timestamp: str


class OffenseAlertRef(BaseModel):
    id: str
    title: str
    severity: str
    status: str
    created_at: str


class OffenseSummary(BaseModel):
    id: str
    offense_number: int
    host_id: str
    host_name: str
    title: str
    description: str | None = None
    risk_level: str
    status: str
    event_count: int
    alert_count: int
    incident_id: str | None = None
    related_hosts: list[str] = []
    related_users: list[str] = []
    created_at: str
    updated_at: str


class OffenseDetail(OffenseSummary):
    timeline: list[dict] = []
    events: list[OffenseEventRef] = []
    alerts: list[OffenseAlertRef] = []


class OffenseListResponse(BaseModel):
    items: list[OffenseSummary]
    total: int
    page: int
    page_size: int
