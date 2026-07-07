from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class UebaAnomalyResponse(BaseModel):
    id: UUID
    entity_type: str
    entity_key: str
    entity_label: str
    metric: str
    observed_value: int
    baseline_mean: float
    baseline_stddev: float
    z_score: float
    severity: str
    status: str
    description: str
    context: dict
    alert_id: UUID | None
    detected_at: datetime
    resolved_at: datetime | None

    model_config = {"from_attributes": True}


class UebaAnomalyUpdate(BaseModel):
    status: str = Field(pattern="^(dismissed|resolved)$")


class UebaSummaryResponse(BaseModel):
    open_count: int
    by_severity: dict[str, int]
    enabled: bool
    z_threshold: float
    baseline_days: int


class UebaScanResponse(BaseModel):
    enabled: bool
    created: int = 0
    updated: int = 0
    hosts_scanned: int = 0
    users_scanned: int = 0
