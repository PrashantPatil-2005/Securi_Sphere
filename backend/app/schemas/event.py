from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.validators import InetStr


class EventResponse(BaseModel):
    id: UUID
    host_id: UUID
    event_type: str
    severity: str
    description: str | None
    source: str | None
    source_ip: InetStr = None
    raw_log: str | None
    timestamp: datetime

    model_config = {"from_attributes": True}


class EventListResponse(BaseModel):
    items: list[EventResponse]
    total: int
    page: int
    page_size: int
    next_cursor: str | None = None
    has_more: bool = False
