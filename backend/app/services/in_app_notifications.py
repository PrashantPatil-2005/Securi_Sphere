"""Persisted in-app notification history."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.in_app_notification import InAppNotification, InAppNotificationRead


async def record_in_app_notification(
    db: AsyncSession,
    *,
    kind: str,
    title: str,
    body: str | None = None,
    severity: str | None = None,
    resource_type: str | None = None,
    resource_id: UUID | None = None,
) -> InAppNotification:
    row = InAppNotification(
        kind=kind,
        title=title,
        body=body,
        severity=severity,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    db.add(row)
    await db.flush()
    return row


async def list_notification_history(
    db: AsyncSession,
    user_id: UUID,
    *,
    page: int = 1,
    page_size: int = 20,
    unread_only: bool = False,
) -> tuple[list[dict], int, int]:
    read_subq = (
        select(InAppNotificationRead.notification_id)
        .where(InAppNotificationRead.user_id == user_id)
        .subquery()
    )

    base = select(InAppNotification).order_by(InAppNotification.created_at.desc())
    if unread_only:
        base = base.where(~InAppNotification.id.in_(select(read_subq.c.notification_id)))

    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()

    unread_count = (
        await db.execute(
            select(func.count())
            .select_from(InAppNotification)
            .where(~InAppNotification.id.in_(select(read_subq.c.notification_id)))
        )
    ).scalar_one()

    rows = (
        await db.execute(base.offset((page - 1) * page_size).limit(page_size))
    ).scalars().all()

    if not rows:
        return [], total, unread_count

    read_ids = set(
        (
            await db.execute(
                select(InAppNotificationRead.notification_id).where(
                    InAppNotificationRead.user_id == user_id,
                    InAppNotificationRead.notification_id.in_([r.id for r in rows]),
                )
            )
        ).scalars().all()
    )

    items = [
        {
            "id": row.id,
            "kind": row.kind,
            "title": row.title,
            "body": row.body,
            "severity": row.severity,
            "resource_type": row.resource_type,
            "resource_id": row.resource_id,
            "created_at": row.created_at,
            "read": row.id in read_ids,
        }
        for row in rows
    ]
    return items, total, unread_count


async def mark_notification_read(db: AsyncSession, user_id: UUID, notification_id: UUID) -> bool:
    exists = (
        await db.execute(select(InAppNotification.id).where(InAppNotification.id == notification_id))
    ).scalar_one_or_none()
    if not exists:
        return False

    already = (
        await db.execute(
            select(InAppNotificationRead.notification_id).where(
                InAppNotificationRead.user_id == user_id,
                InAppNotificationRead.notification_id == notification_id,
            )
        )
    ).scalar_one_or_none()
    if already:
        return True

    db.add(InAppNotificationRead(user_id=user_id, notification_id=notification_id))
    await db.flush()
    return True


async def mark_all_notifications_read(db: AsyncSession, user_id: UUID) -> int:
    unread_ids = (
        await db.execute(
            select(InAppNotification.id).where(
                ~InAppNotification.id.in_(
                    select(InAppNotificationRead.notification_id).where(
                        InAppNotificationRead.user_id == user_id
                    )
                )
            )
        )
    ).scalars().all()

    for nid in unread_ids:
        db.add(InAppNotificationRead(user_id=user_id, notification_id=nid))
    await db.flush()
    return len(unread_ids)


async def unread_notification_count(db: AsyncSession, user_id: UUID) -> int:
    read_subq = (
        select(InAppNotificationRead.notification_id)
        .where(InAppNotificationRead.user_id == user_id)
        .subquery()
    )
    return (
        await db.execute(
            select(func.count())
            .select_from(InAppNotification)
            .where(~InAppNotification.id.in_(select(read_subq.c.notification_id)))
        )
    ).scalar_one()
