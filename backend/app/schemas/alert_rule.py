"""Alert rule schemas."""

from uuid import UUID

from pydantic import BaseModel


class RuleCreate(BaseModel):
    name: str
    rule_type: str
    threshold: float | None = None
    window_minutes: int | None = 5
    severity: str = "medium"


class RuleUpdate(BaseModel):
    threshold: float | None = None
    window_minutes: int | None = None
    severity: str | None = None
    enabled: bool | None = None


class RuleResponse(BaseModel):
    id: UUID
    name: str
    rule_type: str
    threshold: float | None
    window_minutes: int | None
    severity: str
    enabled: bool
    false_positive_count: int = 0
    true_positive_count: int = 0
    model_config = {"from_attributes": True}
