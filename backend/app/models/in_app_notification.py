import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class InAppNotification(Base):
    __tablename__ = "in_app_notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str | None] = mapped_column(String(20))
    resource_type: Mapped[str | None] = mapped_column(String(30))
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )


class InAppNotificationRead(Base):
    __tablename__ = "in_app_notification_reads"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    notification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("in_app_notifications.id", ondelete="CASCADE"), primary_key=True
    )
    read_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
