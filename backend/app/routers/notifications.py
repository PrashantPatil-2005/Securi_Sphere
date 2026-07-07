from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.notification import NotificationSettings
from app.models.notification_rule import NOTIFICATION_TRIGGERS, SEVERITY_LEVELS, NotificationRule
from app.models.user import User
from app.services.in_app_notifications import (
    list_notification_history,
    mark_all_notifications_read,
    mark_notification_read,
    unread_notification_count,
)
from app.config import settings
from app.services.notification_rules import send_delivery_settings_test, send_test_notification
from app.schemas.notification_rule import (
    NotificationRuleCreate,
    NotificationRuleResponse,
    NotificationRuleUpdate,
    NotificationTestResponse,
    NotificationChannels,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


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


def _settings_response(row: NotificationSettings) -> NotificationSettingsResponse:
    return NotificationSettingsResponse(
        email_enabled=row.email_enabled,
        email_address=row.email_address,
        telegram_enabled=row.telegram_enabled,
        telegram_chat_id=row.telegram_chat_id,
        slack_enabled=row.slack_enabled,
        slack_webhook_url=row.slack_webhook_url,
        server_email_configured=bool(settings.smtp_user and settings.smtp_password),
        server_telegram_configured=bool(settings.telegram_bot_token),
    )


class NotificationSettingsUpdate(BaseModel):
    email_enabled: bool | None = None
    email_address: str | None = None
    telegram_enabled: bool | None = None
    telegram_chat_id: str | None = None
    slack_enabled: bool | None = None
    slack_webhook_url: str | None = None


class DeliverySettingsTestRequest(BaseModel):
    channels: NotificationChannels = Field(default_factory=lambda: NotificationChannels(email=True, slack=True, telegram=True))
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
    return _settings_response(await _get_or_create_settings(db, user.id))


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
    return _settings_response(settings_row)


@router.post("/settings/test", response_model=NotificationTestResponse)
async def test_delivery_settings(
    body: DeliverySettingsTestRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    sent = await send_delivery_settings_test(
        db,
        user.id,
        body.channels.model_dump(),
        email_enabled=body.email_enabled,
        email_address=body.email_address,
        telegram_enabled=body.telegram_enabled,
        telegram_chat_id=body.telegram_chat_id,
        slack_enabled=body.slack_enabled,
        slack_webhook_url=body.slack_webhook_url,
    )
    if not sent:
        raise HTTPException(
            status_code=400,
            detail="No channels delivered — enable the channel, provide address/webhook, and select it for test",
        )
    return NotificationTestResponse(channels_sent=sent)


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


def _rule_response(rule: NotificationRule) -> NotificationRuleResponse:
    ch = rule.channels or {}
    return NotificationRuleResponse(
        id=rule.id,
        name=rule.name,
        trigger_event=rule.trigger_event,
        min_severity=rule.min_severity,
        channels=NotificationChannels(
            email=bool(ch.get("email")),
            slack=bool(ch.get("slack")),
            telegram=bool(ch.get("telegram")),
        ),
        enabled=rule.enabled,
        created_at=rule.created_at,
    )


@router.get("/rules", response_model=list[NotificationRuleResponse])
async def list_notification_rules(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = list(
        (
            await db.execute(
                select(NotificationRule)
                .where(NotificationRule.user_id == user.id)
                .order_by(NotificationRule.created_at.desc())
            )
        ).scalars().all()
    )
    return [_rule_response(r) for r in rows]


@router.post("/rules", response_model=NotificationRuleResponse, status_code=201)
async def create_notification_rule(
    body: NotificationRuleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if body.trigger_event not in NOTIFICATION_TRIGGERS:
        raise HTTPException(status_code=400, detail=f"trigger_event must be one of: {', '.join(sorted(NOTIFICATION_TRIGGERS))}")
    if body.min_severity not in SEVERITY_LEVELS:
        raise HTTPException(status_code=400, detail=f"min_severity must be one of: {', '.join(SEVERITY_LEVELS)}")
    rule = NotificationRule(
        user_id=user.id,
        name=body.name.strip(),
        trigger_event=body.trigger_event,
        min_severity=body.min_severity,
        channels=body.channels.model_dump(),
        enabled=body.enabled,
    )
    db.add(rule)
    await db.flush()
    return _rule_response(rule)


@router.patch("/rules/{rule_id}", response_model=NotificationRuleResponse)
async def update_notification_rule(
    rule_id: UUID,
    body: NotificationRuleUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rule = (
        await db.execute(
            select(NotificationRule).where(NotificationRule.id == rule_id, NotificationRule.user_id == user.id)
        )
    ).scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    if body.trigger_event is not None:
        if body.trigger_event not in NOTIFICATION_TRIGGERS:
            raise HTTPException(status_code=400, detail="Invalid trigger_event")
        rule.trigger_event = body.trigger_event
    if body.min_severity is not None:
        if body.min_severity not in SEVERITY_LEVELS:
            raise HTTPException(status_code=400, detail="Invalid min_severity")
        rule.min_severity = body.min_severity
    if body.name is not None:
        rule.name = body.name.strip()
    if body.channels is not None:
        rule.channels = body.channels.model_dump()
    if body.enabled is not None:
        rule.enabled = body.enabled
    await db.flush()
    return _rule_response(rule)


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_notification_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rule = (
        await db.execute(
            select(NotificationRule).where(NotificationRule.id == rule_id, NotificationRule.user_id == user.id)
        )
    ).scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    await db.delete(rule)


@router.post("/rules/{rule_id}/test", response_model=NotificationTestResponse)
async def test_notification_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rule = (
        await db.execute(
            select(NotificationRule).where(NotificationRule.id == rule_id, NotificationRule.user_id == user.id)
        )
    ).scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    sent = await send_test_notification(db, user.id, rule.channels or {})
    return NotificationTestResponse(channels_sent=sent)
