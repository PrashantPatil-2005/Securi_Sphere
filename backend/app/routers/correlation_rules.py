"""Read-only correlation rules API."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.correlation import CorrelationRule
from app.models.user import User

router = APIRouter(prefix="/correlation-rules", tags=["correlation-rules"])


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


def _rule_type(rule: CorrelationRule) -> str:
    desc = rule.description or ""
    if desc.startswith("[cross_host]"):
        return "cross_host"
    if desc.startswith("[co_occurrence]"):
        return "co_occurrence"
    return "sequence"


@router.get("", response_model=list[CorrelationRuleResponse])
async def list_correlation_rules(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    rules = (await db.execute(select(CorrelationRule).order_by(CorrelationRule.name))).scalars().all()
    return [
        CorrelationRuleResponse(
            id=str(r.id),
            name=r.name,
            description=r.description,
            event_sequence=r.event_sequence or [],
            window_minutes=r.window_minutes or 20,
            min_occurrences=r.min_occurrences or {},
            severity=r.severity,
            confidence_base=r.confidence_base or 0.75,
            enabled=r.enabled,
            is_system=r.is_system,
            rule_type=_rule_type(r),
        )
        for r in rules
    ]
