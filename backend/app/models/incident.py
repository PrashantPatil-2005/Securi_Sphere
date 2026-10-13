import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    host_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("hosts.id"))
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confidence: Mapped[float] = mapped_column(default=0.0)
    first_observed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_observed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    affected_hosts: Mapped[list] = mapped_column(JSONB, default=list)
    affected_users: Mapped[list] = mapped_column(JSONB, default=list)
    affected_services: Mapped[list] = mapped_column(JSONB, default=list)
    affected_containers: Mapped[list] = mapped_column(JSONB, default=list)
    mitre_technique_ids: Mapped[list] = mapped_column(JSONB, default=list)
    mitre_tactics: Mapped[list] = mapped_column(JSONB, default=list)
    simulated: Mapped[bool] = mapped_column(default=False)
    source: Mapped[str | None] = mapped_column(String(20), default=None)

    notes: Mapped[list["IncidentNote"]] = relationship("IncidentNote", back_populates="incident")
    alert_links: Mapped[list["IncidentAlert"]] = relationship("IncidentAlert", back_populates="incident")


class IncidentNote(Base):
    __tablename__ = "incident_notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("incidents.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    incident: Mapped["Incident"] = relationship("Incident", back_populates="notes")


class IncidentAlert(Base):
    __tablename__ = "incident_alerts"

    incident_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("incidents.id"), primary_key=True)
    alert_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("alerts.id"), primary_key=True)
    incident: Mapped["Incident"] = relationship("Incident", back_populates="alert_links")
