import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.alert import Alert
from app.models.notification import NotificationSettings

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, body: str) -> None:
    if not settings.smtp_user or not settings.smtp_password:
        logger.info("Email (dev mode): to=%s subject=%s", to, subject)
        return
    try:
        import aiosmtplib
        from email.mime.text import MIMEText

        msg = MIMEText(body, "html")
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from
        msg["To"] = to
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=True,
        )
    except Exception as e:
        logger.error("Failed to send email: %s", e)


async def send_telegram(chat_id: str, message: str) -> None:
    if not settings.telegram_bot_token:
        logger.info("Telegram (dev mode): chat=%s msg=%s", chat_id, message)
        return
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"})
    except Exception as e:
        logger.error("Failed to send Telegram: %s", e)


async def send_slack(webhook_url: str, message: str) -> None:
    if not webhook_url:
        return
    try:
        async with httpx.AsyncClient() as client:
            await client.post(webhook_url, json={"text": message}, timeout=10.0)
    except Exception as e:
        logger.error("Failed to send Slack notification: %s", e)


async def notify_alert(db: AsyncSession, alert: Alert) -> None:
    if alert.severity not in ("critical", "high"):
        return
    message = f"[{alert.severity.upper()}] {alert.title}\n{alert.description or ''}"
    html_message = f"<b>[{alert.severity.upper()}]</b> {alert.title}\n{alert.description or ''}"
    result = await db.execute(select(NotificationSettings).where(NotificationSettings.email_enabled.is_(True)))
    for settings_row in result.scalars().all():
        if settings_row.email_address:
            await send_email(settings_row.email_address, f"Securi Alert: {alert.title}", html_message)

    result = await db.execute(select(NotificationSettings).where(NotificationSettings.telegram_enabled.is_(True)))
    for settings_row in result.scalars().all():
        if settings_row.telegram_chat_id:
            await send_telegram(settings_row.telegram_chat_id, html_message)

    result = await db.execute(select(NotificationSettings).where(NotificationSettings.slack_enabled.is_(True)))
    for settings_row in result.scalars().all():
        if settings_row.slack_webhook_url:
            await send_slack(settings_row.slack_webhook_url, message)


async def notify_offense(db: AsyncSession, offense) -> None:
    if offense.risk_level not in ("critical", "high"):
        return
    message = f"[OFFENSE {offense.risk_level.upper()}] #{offense.offense_number} {offense.title}"
    html_message = f"<b>[OFFENSE {offense.risk_level.upper()}]</b> #{offense.offense_number} {offense.title}"
    result = await db.execute(select(NotificationSettings).where(NotificationSettings.email_enabled.is_(True)))
    for settings_row in result.scalars().all():
        if settings_row.email_address:
            await send_email(settings_row.email_address, f"Securi Offense: {offense.title}", html_message)
    result = await db.execute(select(NotificationSettings).where(NotificationSettings.telegram_enabled.is_(True)))
    for settings_row in result.scalars().all():
        if settings_row.telegram_chat_id:
            await send_telegram(settings_row.telegram_chat_id, html_message)
    result = await db.execute(select(NotificationSettings).where(NotificationSettings.slack_enabled.is_(True)))
    for settings_row in result.scalars().all():
        if settings_row.slack_webhook_url:
            await send_slack(settings_row.slack_webhook_url, message)
