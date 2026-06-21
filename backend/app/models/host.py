import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Host(Base):
    __tablename__ = "hosts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hostname: Mapped[str | None] = mapped_column(String(255))
    ip_address: Mapped[str | None] = mapped_column(INET)
    os_info: Mapped[str | None] = mapped_column(String(255))
    api_key_hash: Mapped[str | None] = mapped_column(String(64))
    api_key_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    api_key_revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    agent_hash: Mapped[str | None] = mapped_column(String(64))
    agent_version: Mapped[str | None] = mapped_column(String(20))
    agent_hash_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    health_status: Mapped[str] = mapped_column(String(20), default="healthy")
    status: Mapped[str] = mapped_column(String(20), default="offline", index=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    enrollment_tokens: Mapped[list["EnrollmentToken"]] = relationship(
        "EnrollmentToken", back_populates="host"
    )
    events: Mapped[list["Event"]] = relationship("Event", back_populates="host")
    metrics: Mapped[list["Metric"]] = relationship("Metric", back_populates="host")
    alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="host")
