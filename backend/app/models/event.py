import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    host_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("hosts.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    mitre_technique_id: Mapped[str | None] = mapped_column(String(20), index=True)
    mitre_tactic: Mapped[str | None] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(50), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(50))
    source_ip: Mapped[str | None] = mapped_column(INET, index=True)
    username: Mapped[str | None] = mapped_column(String(255), index=True)
    raw_log: Mapped[str | None] = mapped_column(Text)
    raw_event: Mapped[str | None] = mapped_column(Text)
    normalized_event: Mapped[dict | None] = mapped_column(JSONB)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    host: Mapped["Host"] = relationship("Host", back_populates="events")
