from uuid import UUID

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class AssistantChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    alert_id: UUID | None = None
    offense_id: UUID | None = None
    siem_query: str | None = None
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)


class AssistantChatResponse(BaseModel):
    reply: str
    provider: str
    suggestions: list[str] = Field(default_factory=list)


class NLSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)


class NLSearchResponse(BaseModel):
    siem_query: str
    explanation: str
    provider: str
    confidence: str


class AlertAISummaryResponse(BaseModel):
    alert_id: str
    summary: str
    investigation_steps: list[str]
    recommended_actions: list[str]
    provider: str


class OffenseAIBriefResponse(BaseModel):
    offense_id: str
    brief: str
    key_findings: list[str]
    recommended_actions: list[str]
    provider: str
