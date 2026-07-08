import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    threshold: Mapped[float | None] = mapped_column(Float)
    window_minutes: Mapped[int | None] = mapped_column(Integer)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    false_positive_count: Mapped[int] = mapped_column(Integer, default=0)
    true_positive_count: Mapped[int] = mapped_column(Integer, default=0)
    feedback_last_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="rule")
