import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Metric(Base):
    __tablename__ = "metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    host_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("hosts.id"), nullable=False, index=True)
    cpu_percent: Mapped[float | None] = mapped_column(Float)
    memory_percent: Mapped[float | None] = mapped_column(Float)
    disk_percent: Mapped[float | None] = mapped_column(Float)
    network_in: Mapped[int | None] = mapped_column(BigInteger)
    network_out: Mapped[int | None] = mapped_column(BigInteger)
    load_average: Mapped[list[float] | None] = mapped_column(ARRAY(Float))
    uptime_seconds: Mapped[int | None] = mapped_column(BigInteger)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    host: Mapped["Host"] = relationship("Host", back_populates="metrics")
