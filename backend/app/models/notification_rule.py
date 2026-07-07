"""Per-user notification rules — when and how to deliver alerts."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

NOTIFICATION_TRIGGERS = frozenset({"alert_created", "offense_created"})
SEVERITY_LEVELS = ("low", "medium", "high", "critical")
SEVERITY_RANK = {s: i for i, s in enumerate(SEVERITY_LEVELS)}


class NotificationRule(Base):
    __tablename__ = "notification_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    trigger_event: Mapped[str] = mapped_column(String(32), nullable=False)
    min_severity: Mapped[str] = mapped_column(String(16), nullable=False, default="high")
    channels: Mapped[dict] = mapped_column(JSONB, default=lambda: {"email": True, "slack": False, "telegram": False})
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
