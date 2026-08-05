from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_roles
from app.models.alert_rule import AlertRule
from app.models.user import User
from app.schemas.alert_rule import RuleCreate, RuleUpdate, RuleResponse
from app.services.audit import log_audit
from app.services.detection import SUPPORTED_RULE_TYPES

router = APIRouter(prefix="/alert-rules", tags=["alert-rules"])


@router.get("/meta")
async def rules_meta(user: User = Depends(require_roles("admin", "analyst"))):
    return {"supported_rule_types": sorted(SUPPORTED_RULE_TYPES)}


@router.get("", response_model=list[RuleResponse])
async def list_rules(db: AsyncSession = Depends(get_db), user: User = Depends(require_roles("admin", "analyst"))):
    return list((await db.execute(select(AlertRule))).scalars().all())


@router.post("", response_model=RuleResponse)
async def create_rule(body: RuleCreate, db: AsyncSession = Depends(get_db), user: User = Depends(require_roles("admin"))):
    if body.rule_type not in SUPPORTED_RULE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported rule_type. Valid types: {sorted(SUPPORTED_RULE_TYPES)}",
        )
    rule = AlertRule(**body.model_dump())
    db.add(rule)
    await db.flush()
    await log_audit(db, "alert_rule_create", user_id=user.id, resource_type="alert_rule", resource_id=rule.id)
    return rule


@router.patch("/{rule_id}", response_model=RuleResponse)
async def update_rule(rule_id: UUID, body: RuleUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(require_roles("admin"))):
    result = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(rule, k, v)
    await log_audit(db, "alert_rule_update", user_id=user.id, resource_type="alert_rule", resource_id=rule_id)
    return rule


@router.delete("/{rule_id}")
async def delete_rule(rule_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(require_roles("admin"))):
    result = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    await log_audit(db, "alert_rule_delete", user_id=user.id, resource_type="alert_rule", resource_id=rule_id)
    await db.delete(rule)
    return {"message": "deleted"}
