"""Maintenance window schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class MaintenanceCreate(BaseModel):
    host_id: UUID
    reason: str | None = None
    ends_at: datetime


class MaintenanceResponse(BaseModel):
    id: str
    host_id: str
    host_name: str
    reason: str | None
    starts_at: datetime
    ends_at: datetime
    active: bool
