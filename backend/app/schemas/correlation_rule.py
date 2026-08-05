"""Correlation rule schemas."""

from uuid import UUID

from pydantic import BaseModel, Field


class CorrelationRuleResponse(BaseModel):
    id: str
    name: str
    description: str | None
    event_sequence: list
    window_minutes: int
    min_occurrences: dict
    severity: str
    confidence_base: float
    enabled: bool
    is_system: bool
    rule_type: str


class CorrelationRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    rule_type: str = "sequence"
    event_sequence: list[str] = Field(min_length=1)
    window_minutes: int = Field(default=20, ge=1, le=1440)
    min_occurrences: dict = Field(default_factory=dict)
    severity: str = "high"
    confidence_base: float = Field(default=0.75, ge=0.0, le=1.0)


class CorrelationRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    rule_type: str | None = None
    event_sequence: list[str] | None = Field(default=None, min_length=1)
    window_minutes: int | None = Field(default=None, ge=1, le=1440)
    min_occurrences: dict | None = None
    severity: str | None = None
    confidence_base: float | None = Field(default=None, ge=0.0, le=1.0)
    enabled: bool | None = None


class CorrelationRuleValidateRequest(BaseModel):
    rule_type: str = "sequence"
    event_sequence: list[str] = Field(min_length=1)
    window_minutes: int = Field(default=20, ge=1, le=1440)
    min_occurrences: dict = Field(default_factory=dict)
    severity: str = "high"
    confidence_base: float = Field(default=0.75, ge=0.0, le=1.0)


class CorrelationRulePreviewRequest(CorrelationRuleValidateRequest):
    host_id: UUID | None = None
