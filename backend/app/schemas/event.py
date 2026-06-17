from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class EventResponse(BaseModel):
    id: UUID
    host_id: UUID
    event_type: str
    severity: str
    description: str | None
    source: str | None
    raw_log: str | None
    timestamp: datetime

    model_config = {"from_attributes": True}


class EventListResponse(BaseModel):
    items: list[EventResponse]
    total: int
    page: int
    page_size: int
