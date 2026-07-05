from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.notification import NotificationSettings
from app.models.user import User
from app.services.in_app_notifications import (
    list_notification_history,
    mark_all_notifications_read,
    mark_notification_read,
    unread_notification_count,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationSettingsResponse(BaseModel):
    email_enabled: bool
    email_address: str | None
    telegram_enabled: bool
    telegram_chat_id: str | None
    slack_enabled: bool
    slack_webhook_url: str | None

    model_config = {"from_attributes": True}


class NotificationSettingsUpdate(BaseModel):
    email_enabled: bool | None = None
    email_address: str | None = None
    telegram_enabled: bool | None = None
    telegram_chat_id: str | None = None
    slack_enabled: bool | None = None
    slack_webhook_url: str | None = None


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


async def _get_or_create_settings(db: AsyncSession, user_id: UUID) -> NotificationSettings:
    row = (
        await db.execute(select(NotificationSettings).where(NotificationSettings.user_id == user_id))
    ).scalar_one_or_none()
    if row:
        return row
    row = NotificationSettings(user_id=user_id)
    db.add(row)
    await db.flush()
    return row


@router.get("/settings", response_model=NotificationSettingsResponse)
async def get_notification_settings(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await _get_or_create_settings(db, user.id)


@router.patch("/settings", response_model=NotificationSettingsResponse)
async def update_notification_settings(
    body: NotificationSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    settings_row = await _get_or_create_settings(db, user.id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(settings_row, key, value)
    await db.flush()
    return settings_row


@router.get("/history", response_model=NotificationHistoryResponse)
async def get_notification_history(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = False,
):
    items, total, unread = await list_notification_history(
        db, user.id, page=page, page_size=page_size, unread_only=unread_only
    )
    return NotificationHistoryResponse(
        items=[NotificationHistoryItem.model_validate(i) for i in items],
        total=total,
        unread_count=unread,
        page=page,
        page_size=page_size,
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    count = await unread_notification_count(db, user.id)
    return UnreadCountResponse(unread_count=count)


@router.patch("/{notification_id}/read")
async def mark_read(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ok = await mark_notification_read(db, user.id, notification_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"ok": True}


@router.post("/read-all", response_model=MarkAllReadResponse)
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    marked = await mark_all_notifications_read(db, user.id)
    return MarkAllReadResponse(marked=marked)
