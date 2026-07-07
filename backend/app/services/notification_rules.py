"""Notification rule evaluation and delivery."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.brand import PRODUCT_NAME
from app.models.notification import NotificationSettings
from app.models.notification_rule import SEVERITY_RANK, NotificationRule
from app.services.notifications import send_email, send_slack, send_telegram

logger = logging.getLogger(__name__)


def severity_meets_minimum(actual: str, minimum: str) -> bool:
    return SEVERITY_RANK.get(actual, 0) >= SEVERITY_RANK.get(minimum, 0)


async def _send_to_user_channels(
    settings_row: NotificationSettings,
    channels: dict,
    *,
    subject: str,
    plain: str,
    html: str,
) -> list[str]:
    sent: list[str] = []
    if channels.get("email") and settings_row.email_enabled and settings_row.email_address:
        await send_email(settings_row.email_address, subject, html)
        sent.append("email")
    if channels.get("telegram") and settings_row.telegram_enabled and settings_row.telegram_chat_id:
        await send_telegram(settings_row.telegram_chat_id, html)
        sent.append("telegram")
    if channels.get("slack") and settings_row.slack_enabled and settings_row.slack_webhook_url:
        await send_slack(settings_row.slack_webhook_url, plain)
        sent.append("slack")
    return sent


async def dispatch_notification_rules(
    db: AsyncSession,
    *,
    trigger_event: str,
    severity: str,
    subject: str,
    plain_body: str,
    html_body: str,
) -> int:
    """Evaluate all enabled rules for this trigger/severity. Returns deliveries count."""
    rules = list(
        (
            await db.execute(
                select(NotificationRule, NotificationSettings)
                .join(NotificationSettings, NotificationSettings.user_id == NotificationRule.user_id)
                .where(NotificationRule.enabled.is_(True), NotificationRule.trigger_event == trigger_event)
            )
        ).all()
    )
    deliveries = 0
    for rule, settings_row in rules:
        if not severity_meets_minimum(severity, rule.min_severity):
            continue
        sent = await _send_to_user_channels(
            settings_row,
            rule.channels or {},
            subject=subject,
            plain=plain_body,
            html=html_body,
        )
        if sent:
            deliveries += 1
            logger.info(
                "notification rule fired",
                extra={"rule": rule.name, "user_id": str(rule.user_id), "channels": sent},
            )
    return deliveries


async def send_test_notification(
    db: AsyncSession,
    user_id,
    channels: dict,
) -> list[str]:
    settings_row = (
        await db.execute(select(NotificationSettings).where(NotificationSettings.user_id == user_id))
    ).scalar_one_or_none()
    if not settings_row:
        settings_row = NotificationSettings(user_id=user_id)
        db.add(settings_row)
        await db.flush()
    subject = f"{PRODUCT_NAME} test notification"
    plain = f"This is a test notification from your {PRODUCT_NAME} notification rule."
    html = f"<b>{PRODUCT_NAME} test</b><br/>This is a test notification from your notification rule."
    return await _send_to_user_channels(settings_row, channels, subject=subject, plain=plain, html=html)


def _merge_settings_for_test(
    settings_row: NotificationSettings,
    *,
    email_enabled: bool | None = None,
    email_address: str | None = None,
    slack_enabled: bool | None = None,
    slack_webhook_url: str | None = None,
    telegram_enabled: bool | None = None,
    telegram_chat_id: str | None = None,
) -> NotificationSettings:
    """Overlay unsaved form values for delivery test without persisting."""
    merged = NotificationSettings(user_id=settings_row.user_id)
    merged.email_enabled = email_enabled if email_enabled is not None else settings_row.email_enabled
    merged.email_address = email_address if email_address is not None else settings_row.email_address
    merged.slack_enabled = slack_enabled if slack_enabled is not None else settings_row.slack_enabled
    merged.slack_webhook_url = slack_webhook_url if slack_webhook_url is not None else settings_row.slack_webhook_url
    merged.telegram_enabled = telegram_enabled if telegram_enabled is not None else settings_row.telegram_enabled
    merged.telegram_chat_id = telegram_chat_id if telegram_chat_id is not None else settings_row.telegram_chat_id
    return merged


async def send_delivery_settings_test(
    db: AsyncSession,
    user_id,
    channels: dict,
    *,
    email_enabled: bool | None = None,
    email_address: str | None = None,
    slack_enabled: bool | None = None,
    slack_webhook_url: str | None = None,
    telegram_enabled: bool | None = None,
    telegram_chat_id: str | None = None,
) -> list[str]:
    settings_row = (
        await db.execute(select(NotificationSettings).where(NotificationSettings.user_id == user_id))
    ).scalar_one_or_none()
    if not settings_row:
        settings_row = NotificationSettings(user_id=user_id)
        db.add(settings_row)
        await db.flush()
    effective = _merge_settings_for_test(
        settings_row,
        email_enabled=email_enabled,
        email_address=email_address,
        slack_enabled=slack_enabled,
        slack_webhook_url=slack_webhook_url,
        telegram_enabled=telegram_enabled,
        telegram_chat_id=telegram_chat_id,
    )
    subject = f"{PRODUCT_NAME} delivery test"
    plain = f"This is a test message from your {PRODUCT_NAME} delivery settings."
    html = f"<b>{PRODUCT_NAME} delivery test</b><br/>Your notification channel is working."
    return await _send_to_user_channels(effective, channels, subject=subject, plain=plain, html=html)
