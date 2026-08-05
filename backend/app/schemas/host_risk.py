"""Host risk and token schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TokenListItem(BaseModel):
    id: UUID
    expires_at: datetime
    used_at: datetime | None
    revoked_at: datetime | None
    label: str | None
    model_config = {"from_attributes": True}


class RiskFactorItem(BaseModel):
    name: str
    value: float
    weight: float


class RiskHistoryItem(BaseModel):
    risk_score: int
    health_score: int
    recorded_at: datetime


class HostRiskResponse(BaseModel):
    host_id: str
    host_name: str
    score: int
    health_score: int
    factors: dict[str, float]
    factor_breakdown: list[RiskFactorItem]
    history: list[RiskHistoryItem]
