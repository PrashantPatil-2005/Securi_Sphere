"""Offense schemas."""

from pydantic import BaseModel


class OffenseStatusUpdate(BaseModel):
    status: str
