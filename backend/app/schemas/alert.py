from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


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
