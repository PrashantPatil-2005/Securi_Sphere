import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

DEFAULT_WIDGETS = [
    {"id": "kpis", "visible": True},
    {"id": "onboarding", "visible": True},
    {"id": "timeline", "visible": True},
    {"id": "risky_hosts", "visible": True},
    {"id": "attack_timelines", "visible": True},
    {"id": "live_feed", "visible": True},
]


class DashboardLayout(Base):
    __tablename__ = "dashboard_layouts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    widgets: Mapped[list] = mapped_column(JSONB, nullable=False, default=lambda: list(DEFAULT_WIDGETS))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
