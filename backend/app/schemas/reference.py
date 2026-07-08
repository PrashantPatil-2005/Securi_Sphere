from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ReferenceSetEntryResponse(BaseModel):
    id: UUID
    value: str
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReferenceSetResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    set_type: str
    enabled: bool
    source_type: str = "manual"
    feed_url: str | None = None
    feed_format: str | None = None
    feed_last_sync_at: datetime | None = None
    feed_last_sync_status: str | None = None
    feed_last_sync_error: str | None = None
    entry_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class ReferenceSetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    set_type: str = "ip"
    enabled: bool = True
    source_type: str = "manual"
    feed_url: str | None = Field(default=None, max_length=2000)
    feed_format: str | None = Field(default=None, pattern="^(txt|csv|json)$")


class ReferenceSetUpdate(BaseModel):
    description: str | None = None
    enabled: bool | None = None
    source_type: str | None = None
    feed_url: str | None = Field(default=None, max_length=2000)
    feed_format: str | None = Field(default=None, pattern="^(txt|csv|json)$")


class ReferenceSetEntriesBulk(BaseModel):
    values: list[str] = Field(min_length=1, max_length=500)
    note: str | None = Field(default=None, max_length=255)


class ReferenceLookupResponse(BaseModel):
    value: str
    matches: list[dict]


class BuildingBlockResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    category: str
    siem_query: str
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class BuildingBlockCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    category: str = "custom"
    siem_query: str = Field(min_length=1, max_length=2000)
    enabled: bool = True


class BuildingBlockUpdate(BaseModel):
    description: str | None = None
    category: str | None = None
    siem_query: str | None = Field(default=None, min_length=1, max_length=2000)
    enabled: bool | None = None
