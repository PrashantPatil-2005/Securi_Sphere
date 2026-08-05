"""Timeline schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TimelineResponse(BaseModel):
    id: UUID
    host_id: UUID
    title: str
    description: str | None
    started_at: datetime
    ended_at: datetime
    event_ids: list
    mitre_techniques: list
    severity: str
    confidence: float
    status: str
    model_config = {"from_attributes": True}


class TimelineEventResponse(BaseModel):
    id: UUID
    event_type: str
    severity: str
    description: str | None
    mitre_technique_id: str | None
    timestamp: datetime
    model_config = {"from_attributes": True}
