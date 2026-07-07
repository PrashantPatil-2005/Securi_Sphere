"""SOAR playbook definitions and execution audit."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

PLAYBOOK_TRIGGERS = frozenset({
    "alert_created",
    "offense_created",
    "incident_created",
    "alert_status_changed",
})

SEVERITY_LEVELS = ("info", "low", "medium", "high", "critical")


class Playbook(Base):
    __tablename__ = "playbooks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    trigger_event: Mapped[str] = mapped_column(String(64), nullable=False)
    min_severity: Mapped[str | None] = mapped_column(String(16))
    webhook_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    webhook_secret: Mapped[str | None] = mapped_column(String(255))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    runs: Mapped[list["PlaybookRun"]] = relationship("PlaybookRun", back_populates="playbook", cascade="all, delete-orphan")


class PlaybookRun(Base):
    __tablename__ = "playbook_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    playbook_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("playbooks.id", ondelete="CASCADE"))
    trigger_event: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    playbook: Mapped["Playbook"] = relationship("Playbook", back_populates="runs")
