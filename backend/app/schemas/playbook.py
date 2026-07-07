from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PlaybookResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    trigger_event: str
    min_severity: str | None
    webhook_url: str
    has_secret: bool = False
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PlaybookCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    trigger_event: str
    min_severity: str | None = None
    webhook_url: str = Field(min_length=8, max_length=1024)
    webhook_secret: str | None = Field(default=None, max_length=255)
    enabled: bool = True


class PlaybookUpdate(BaseModel):
    description: str | None = None
    trigger_event: str | None = None
    min_severity: str | None = None
    webhook_url: str | None = Field(default=None, min_length=8, max_length=1024)
    webhook_secret: str | None = None
    enabled: bool | None = None


class PlaybookRunResponse(BaseModel):
    id: UUID
    playbook_id: UUID
    trigger_event: str
    status: str
    http_status: int | None
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PlaybookTestResponse(BaseModel):
    status: str
    http_status: int | None = None
    error_message: str | None = None
