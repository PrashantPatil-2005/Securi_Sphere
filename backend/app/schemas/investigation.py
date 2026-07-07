from datetime import datetime, timedelta
from uuid import UUID

from pydantic import BaseModel

from app.schemas.alert import (
    AlertInvestigationHost,
    AlertInvestigationTimeline,
    AlertResponse,
)
from app.schemas.event import EventResponse


class WorkspaceAnchor(BaseModel):
    type: str
    id: UUID


class WorkspaceOffenseSummary(BaseModel):
    id: UUID
    offense_number: int
    host_id: UUID
    host_name: str | None = None
    title: str
    description: str | None = None
    risk_level: str
    status: str
    event_count: int
    alert_count: int
    incident_id: UUID | None = None
    timeline: list = []
    related_users: list = []
    alerts: list[dict] = []
    events: list[dict] = []


class WorkspaceIncidentSummary(BaseModel):
    id: UUID
    title: str
    description: str | None = None
    severity: str
    status: str
    host_id: UUID | None = None
    created_at: datetime
    resolved_at: datetime | None = None
    notes: list[dict] = []
    alert_ids: list[str] = []


class InvestigationWorkspaceResponse(BaseModel):
    anchor: WorkspaceAnchor
    alert: AlertResponse | None = None
    offense: WorkspaceOffenseSummary | None = None
    incident: WorkspaceIncidentSummary | None = None
    host: AlertInvestigationHost | None = None
    events: list[EventResponse] = []
    timelines: list[AlertInvestigationTimeline] = []
    linked_alerts: list[AlertResponse] = []
