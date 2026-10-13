from datetime import datetime
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
    created_at: datetime | None = None
    timeline: list = []
    related_users: list = []
    alerts: list[dict] = []
    events: list[dict] = []


class WorkspaceNote(BaseModel):
    id: UUID
    content: str
    user_id: UUID
    user_email: str | None = None
    created_at: datetime


class WorkspaceIncidentSummary(BaseModel):
    id: UUID
    title: str
    description: str | None = None
    severity: str
    status: str
    host_id: UUID | None = None
    assigned_to: UUID | None = None
    assignee_email: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    resolved_at: datetime | None = None
    confidence: float | None = None
    first_observed: datetime | None = None
    last_observed: datetime | None = None
    affected_hosts: list = []
    affected_users: list = []
    affected_services: list = []
    mitre_technique_ids: list = []
    mitre_tactics: list = []
    simulated: bool = False
    source: str | None = None
    notes: list[WorkspaceNote] = []
    alert_ids: list[str] = []


class WorkspaceTimelineEntry(BaseModel):
    type: str  # incident | alert | offense | event | note | timeline
    timestamp: datetime
    title: str
    description: str | None = None
    severity: str | None = None
    ref_id: str | None = None
    simulated: bool = False


class WorkspaceEntityHost(BaseModel):
    id: UUID | None = None
    name: str
    ip: str | None = None


class WorkspaceEntities(BaseModel):
    hosts: list[WorkspaceEntityHost] = []
    accounts: list[str] = []
    network_ips: list[str] = []


class WorkspaceMitre(BaseModel):
    technique_ids: list[str] = []
    tactics: list[str] = []


class WorkspaceProvenance(BaseModel):
    simulated: bool = False
    sources: list[str] = []


class InvestigationWorkspaceResponse(BaseModel):
    anchor: WorkspaceAnchor
    alert: AlertResponse | None = None
    offense: WorkspaceOffenseSummary | None = None
    incident: WorkspaceIncidentSummary | None = None
    host: AlertInvestigationHost | None = None
    events: list[EventResponse] = []
    timelines: list[AlertInvestigationTimeline] = []
    linked_alerts: list[AlertResponse] = []
    investigation_timeline: list[WorkspaceTimelineEntry] = []
    entities: WorkspaceEntities = WorkspaceEntities()
    mitre: WorkspaceMitre = WorkspaceMitre()
    provenance: WorkspaceProvenance = WorkspaceProvenance()
    partial_errors: list[str] = []
