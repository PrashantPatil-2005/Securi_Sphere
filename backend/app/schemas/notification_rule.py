from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class NotificationChannels(BaseModel):
    email: bool = True
    slack: bool = False
    telegram: bool = False


class NotificationRuleResponse(BaseModel):
    id: UUID
    name: str
    trigger_event: str
    min_severity: str
    channels: NotificationChannels
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    trigger_event: str
    min_severity: str = "high"
    channels: NotificationChannels = Field(default_factory=NotificationChannels)
    enabled: bool = True


class NotificationRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    trigger_event: str | None = None
    min_severity: str | None = None
    channels: NotificationChannels | None = None
    enabled: bool | None = None


class NotificationTestResponse(BaseModel):
    channels_sent: list[str]
