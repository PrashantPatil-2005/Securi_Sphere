"""Threat score schemas."""

from pydantic import BaseModel


class ScoreResponse(BaseModel):
    host_id: str
    host_name: str
    score: int
    health_score: int
    factors: dict
