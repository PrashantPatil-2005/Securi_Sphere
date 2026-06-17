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
    created_at: datetime
    resolved_at: datetime | None
    resolved_by: UUID | None

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    items: list[AlertResponse]
    total: int
