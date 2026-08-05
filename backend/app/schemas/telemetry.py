"""Telemetry schemas."""

from pydantic import BaseModel, Field


class TelemetryEventIn(BaseModel):
    event: str = Field(..., max_length=100)
    properties: dict | None = None
    session_id: str | None = Field(None, max_length=64)
    page_path: str | None = Field(None, max_length=255)
