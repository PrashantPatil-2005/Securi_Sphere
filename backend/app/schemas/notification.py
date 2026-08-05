"""Notification schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class NotificationSettingsResponse(BaseModel):
    email_enabled: bool
    email_address: str | None
    telegram_enabled: bool
    telegram_chat_id: str | None
    slack_enabled: bool
    slack_webhook_url: str | None
    server_email_configured: bool = False
    server_telegram_configured: bool = False
    model_config = {"from_attributes": True}


class NotificationSettingsUpdate(BaseModel):
    email_enabled: bool | None = None
    email_address: str | None = None
    telegram_enabled: bool | None = None
    telegram_chat_id: str | None = None
    slack_enabled: bool | None = None
    slack_webhook_url: str | None = None


class DeliverySettingsTestRequest(BaseModel):
    channels: "NotificationChannels" = Field(default_factory=lambda: NotificationChannels(email=True, slack=True, telegram=True))
    email_enabled: bool | None = None
    email_address: str | None = None
    telegram_enabled: bool | None = None
    telegram_chat_id: str | None = None
    slack_enabled: bool | None = None
    slack_webhook_url: str | None = None


class NotificationChannels(BaseModel):
    email: bool = True
    slack: bool = True
    telegram: bool = True


class NotificationHistoryItem(BaseModel):
    id: UUID
    kind: str
    title: str
    body: str | None
    severity: str | None
    resource_type: str | None
    resource_id: UUID | None
    created_at: datetime
    read: bool


class NotificationHistoryResponse(BaseModel):
    items: list[NotificationHistoryItem]
    total: int
    unread_count: int
    page: int
    page_size: int


class UnreadCountResponse(BaseModel):
    unread_count: int


class MarkAllReadResponse(BaseModel):
    marked: int
