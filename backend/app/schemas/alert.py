from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.event import EventResponse


class AlertResponse(BaseModel):
    id: UUID
    host_id: UUID
    rule_id: UUID | None
    severity: str
    title: str
    description: str | None
    status: str
    confidence: float | None = None
    assigned_to: UUID | None = None
    mitre_technique_id: str | None = None
    created_at: datetime
    resolved_at: datetime | None
    resolved_by: UUID | None

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    items: list[AlertResponse]
    total: int
    page: int
    page_size: int


class AlertStatusUpdate(BaseModel):
    status: str
    assigned_to: UUID | None = None


class AlertBulkUpdate(BaseModel):
    alert_ids: list[UUID]
    status: str | None = None
    assigned_to: UUID | None = None


class AlertBulkUpdateResponse(BaseModel):
    updated: int
    not_found: list[UUID]


class AlertInvestigationHost(BaseModel):
    id: UUID
    name: str
    hostname: str | None
    status: str
    ip_address: str | None
    risk_score: int | None = None


class AlertInvestigationTimeline(BaseModel):
    id: UUID
    title: str
    severity: str
    confidence: float
    started_at: datetime
    status: str


class AlertInvestigationResponse(BaseModel):
    alert: AlertResponse
    host: AlertInvestigationHost
    events: list[EventResponse]
    timelines: list[AlertInvestigationTimeline]
