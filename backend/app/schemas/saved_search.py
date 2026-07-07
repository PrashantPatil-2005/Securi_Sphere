from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SavedSearchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    query: str = Field(min_length=1)
    alert_enabled: bool = False
    interval_minutes: int = Field(default=5, ge=1, le=1440)


class SavedSearchUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    query: str | None = Field(default=None, min_length=1)
    alert_enabled: bool | None = None
    interval_minutes: int | None = Field(default=None, ge=1, le=1440)


class SavedSearchResponse(BaseModel):
    id: UUID
    name: str
    query: str
    alert_enabled: bool
    interval_minutes: int
    created_at: datetime

    model_config = {"from_attributes": True}
