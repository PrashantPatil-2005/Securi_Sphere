"""QRadar-style reference sets and reusable building blocks."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

REFERENCE_SET_TYPES = frozenset({"ip", "username", "hostname", "domain", "hash", "port"})


class ReferenceSet(Base):
    __tablename__ = "reference_sets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    set_type: Mapped[str] = mapped_column(String(32), nullable=False, default="ip")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    source_type: Mapped[str] = mapped_column(String(16), default="manual")
    feed_url: Mapped[str | None] = mapped_column(Text)
    feed_format: Mapped[str | None] = mapped_column(String(16))
    feed_last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    feed_last_sync_status: Mapped[str | None] = mapped_column(String(16))
    feed_last_sync_error: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    entries: Mapped[list["ReferenceSetEntry"]] = relationship(
        "ReferenceSetEntry", back_populates="reference_set", cascade="all, delete-orphan"
    )


class ReferenceSetEntry(Base):
    __tablename__ = "reference_set_entries"
    __table_args__ = (UniqueConstraint("set_id", "value", name="uq_reference_set_entry"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    set_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reference_sets.id"), index=True)
    value: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    reference_set: Mapped["ReferenceSet"] = relationship("ReferenceSet", back_populates="entries")


class BuildingBlock(Base):
    __tablename__ = "building_blocks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(64), default="custom")
    siem_query: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
