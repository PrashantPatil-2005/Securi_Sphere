"""Correlation rules API — list for all users; CRUD for admins on custom rules."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.correlation import CorrelationRule
from app.models.user import User
from app.services.audit import log_audit

router = APIRouter(prefix="/correlation-rules", tags=["correlation-rules"])

VALID_RULE_TYPES = frozenset({"sequence", "co_occurrence", "cross_host"})
VALID_SEVERITIES = frozenset({"low", "medium", "high", "critical"})


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
    event_sequence: list[str] | None = Field(default=None, min_length=1)
    window_minutes: int | None = Field(default=None, ge=1, le=1440)
    min_occurrences: dict | None = None
    severity: str | None = None
    confidence_base: float | None = Field(default=None, ge=0.0, le=1.0)
    enabled: bool | None = None


def _rule_type(rule: CorrelationRule) -> str:
    desc = rule.description or ""
    if desc.startswith("[cross_host]"):
        return "cross_host"
    if desc.startswith("[co_occurrence]"):
        return "co_occurrence"
    return "sequence"


def _to_response(rule: CorrelationRule) -> CorrelationRuleResponse:
    return CorrelationRuleResponse(
        id=str(rule.id),
        name=rule.name,
        description=rule.description,
        event_sequence=rule.event_sequence or [],
        window_minutes=rule.window_minutes or 20,
        min_occurrences=rule.min_occurrences or {},
        severity=rule.severity,
        confidence_base=rule.confidence_base or 0.75,
        enabled=rule.enabled,
        is_system=rule.is_system,
        rule_type=_rule_type(rule),
    )


def _description_for_type(description: str | None, rule_type: str) -> str | None:
    text = (description or "").strip()
    for prefix in ("[cross_host]", "[co_occurrence]"):
        if text.lower().startswith(prefix):
            text = text[len(prefix):].strip()
    if rule_type == "co_occurrence":
        return f"[co_occurrence] {text}".strip() if text else "[co_occurrence]"
    if rule_type == "cross_host":
        return f"[cross_host] {text}".strip() if text else "[cross_host]"
    return text or None


def _validate_create(body: CorrelationRuleCreate) -> None:
    if body.rule_type not in VALID_RULE_TYPES:
        raise HTTPException(status_code=400, detail=f"rule_type must be one of {sorted(VALID_RULE_TYPES)}")
    if body.severity not in VALID_SEVERITIES:
        raise HTTPException(status_code=400, detail=f"severity must be one of {sorted(VALID_SEVERITIES)}")
    if body.rule_type == "co_occurrence" and len(body.event_sequence) < 2:
        raise HTTPException(status_code=400, detail="co_occurrence rules require at least 2 event types")
    if not all(isinstance(item, str) and item.strip() for item in body.event_sequence):
        raise HTTPException(status_code=400, detail="event_sequence entries must be non-empty strings")


@router.get("", response_model=list[CorrelationRuleResponse])
async def list_correlation_rules(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    rules = (await db.execute(select(CorrelationRule).order_by(CorrelationRule.name))).scalars().all()
    return [_to_response(r) for r in rules]


@router.post("", response_model=CorrelationRuleResponse)
async def create_correlation_rule(
    body: CorrelationRuleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    _validate_create(body)
    existing = (
        await db.execute(select(CorrelationRule).where(CorrelationRule.name == body.name))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="A correlation rule with this name already exists")

    rule = CorrelationRule(
        name=body.name.strip(),
        description=_description_for_type(body.description, body.rule_type),
        event_sequence=body.event_sequence,
        window_minutes=body.window_minutes,
        min_occurrences=body.min_occurrences,
        severity=body.severity,
        confidence_base=body.confidence_base,
        enabled=True,
        is_system=False,
    )
    db.add(rule)
    await db.flush()
    await log_audit(
        db,
        "correlation_rule_create",
        user_id=user.id,
        resource_type="correlation_rule",
        resource_id=rule.id,
        details={"name": rule.name, "rule_type": body.rule_type},
    )
    return _to_response(rule)


@router.patch("/{rule_id}", response_model=CorrelationRuleResponse)
async def update_correlation_rule(
    rule_id: UUID,
    body: CorrelationRuleUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    rule = (await db.execute(select(CorrelationRule).where(CorrelationRule.id == rule_id))).scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Correlation rule not found")

    updates = body.model_dump(exclude_unset=True)
    if rule.is_system:
        allowed = {"enabled", "severity"}
        disallowed = set(updates) - allowed
        if disallowed:
            raise HTTPException(
                status_code=400,
                detail=f"System rules only allow updating: {sorted(allowed)}",
            )

    if "severity" in updates and updates["severity"] not in VALID_SEVERITIES:
        raise HTTPException(status_code=400, detail=f"severity must be one of {sorted(VALID_SEVERITIES)}")
    if "event_sequence" in updates:
        if not updates["event_sequence"]:
            raise HTTPException(status_code=400, detail="event_sequence cannot be empty")
        if _rule_type(rule) == "co_occurrence" and len(updates["event_sequence"]) < 2:
            raise HTTPException(status_code=400, detail="co_occurrence rules require at least 2 event types")

    if "name" in updates and not rule.is_system:
        name = updates["name"].strip()
        clash = (
            await db.execute(
                select(CorrelationRule).where(CorrelationRule.name == name, CorrelationRule.id != rule_id)
            )
        ).scalar_one_or_none()
        if clash:
            raise HTTPException(status_code=400, detail="A correlation rule with this name already exists")
        updates["name"] = name

    if "description" in updates and not rule.is_system:
        updates["description"] = _description_for_type(updates["description"], _rule_type(rule))

    for key, value in updates.items():
        setattr(rule, key, value)

    await log_audit(
        db,
        "correlation_rule_update",
        user_id=user.id,
        resource_type="correlation_rule",
        resource_id=rule.id,
        details={"fields": list(updates.keys())},
    )
    return _to_response(rule)


@router.delete("/{rule_id}")
async def delete_correlation_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    rule = (await db.execute(select(CorrelationRule).where(CorrelationRule.id == rule_id))).scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Correlation rule not found")
    if rule.is_system:
        raise HTTPException(status_code=400, detail="System correlation rules cannot be deleted")

    await log_audit(
        db,
        "correlation_rule_delete",
        user_id=user.id,
        resource_type="correlation_rule",
        resource_id=rule.id,
        details={"name": rule.name},
    )
    await db.delete(rule)
    return {"message": "deleted"}
