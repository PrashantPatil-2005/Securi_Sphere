from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

ALLOWED_SEVERITIES = frozenset({"info", "low", "medium", "high", "critical"})
MAX_CUSTOM_STEPS = 20


class MitreStepInfo(BaseModel):
    technique_id: str
    tactic: str
    name: str


class ScenarioStepResponse(BaseModel):
    order: int
    event_type: str
    offset_seconds: int
    description: str | None = None
    mitre: MitreStepInfo | None = None


class ScenarioResponse(BaseModel):
    id: str
    name: str
    summary: str
    difficulty: str
    event_count: int
    duration_seconds: int
    steps: list[ScenarioStepResponse]
    expected_alerts: list[str]
    expected_outcomes: list[str]


class ScenariosListResponse(BaseModel):
    scenarios: list[ScenarioResponse]
    enabled: bool


class EventTypeOption(BaseModel):
    event_type: str
    category: str


class EventTypesResponse(BaseModel):
    event_types: list[EventTypeOption]


class CustomSimulationStep(BaseModel):
    event_type: str
    offset_seconds: int = Field(ge=0, le=3600)
    severity: str | None = None
    description: str | None = None

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str | None) -> str | None:
        if v is not None and v not in ALLOWED_SEVERITIES:
            raise ValueError(f"severity must be one of {sorted(ALLOWED_SEVERITIES)}")
        return v


class CustomSimulationRequest(BaseModel):
    host_id: UUID
    name: str = Field(min_length=1, max_length=255)
    steps: list[CustomSimulationStep] = Field(min_length=1, max_length=MAX_CUSTOM_STEPS)


class SimulationStepInput(BaseModel):
    event_type: str
    offset_seconds: int
    severity: str | None = None
    description: str | None = None


class SimulationRunResponse(BaseModel):
    message: str
    events: int
    run_id: UUID
    host_id: UUID
    scenario: str
    name: str
    event_ids: list[UUID] = Field(default_factory=list)
    alert_ids: list[UUID] = Field(default_factory=list)
    timeline_ids: list[UUID] = Field(default_factory=list)
    offense_ids: list[UUID] = Field(default_factory=list)


class SimulationRunSummary(BaseModel):
    id: UUID
    scenario_id: str
    name: str
    host_id: UUID
    host_name: str | None = None
    event_count: int
    alert_count: int
    offense_count: int
    timeline_count: int
    created_at: datetime
    run_by: str | None = None

    model_config = {"from_attributes": True}


class SimulationRunListResponse(BaseModel):
    items: list[SimulationRunSummary]
    total: int


class SimulationRunDetail(SimulationRunSummary):
    event_ids: list[UUID] = Field(default_factory=list)
    alert_ids: list[UUID] = Field(default_factory=list)
    timeline_ids: list[UUID] = Field(default_factory=list)
    offense_ids: list[UUID] = Field(default_factory=list)
