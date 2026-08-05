"""Incident schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class IncidentCreate(BaseModel):
    title: str
    description: str | None = None
    severity: str = "medium"
    host_id: UUID | None = None


class NoteCreate(BaseModel):
    content: str


class IncidentResponse(BaseModel):
    id: UUID
    title: str
    description: str | None
    severity: str
    status: str
    host_id: UUID | None
    assigned_to: UUID | None
    created_at: datetime
    resolved_at: datetime | None
    model_config = {"from_attributes": True}


class IncidentDetailResponse(IncidentResponse):
    notes: list[dict] = []
    alert_ids: list[str] = []
