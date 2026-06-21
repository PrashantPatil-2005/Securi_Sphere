from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.notification import NotificationSettings
from app.models.user import User

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
