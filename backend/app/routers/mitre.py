from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, get_db_read
from app.dependencies import get_current_user
from app.models.event import Event
from app.models.mitre import MitreTechnique
from app.models.user import User
from app.schemas.mitre import MitreDrilldownResponse
from app.services.mitre import get_matrix_summary
from app.services.mitre_drilldown import get_technique_drilldown
from app.utils.query import ListParams, resolve_time_range, apply_time_range

router = APIRouter(prefix="/mitre", tags=["mitre"])


class TechniqueResponse(BaseModel):
    technique_id: str
    tactic: str
    name: str
    description: str | None
    model_config = {"from_attributes": True}


@router.get("/techniques", response_model=list[TechniqueResponse])
async def list_techniques(db: AsyncSession = Depends(get_db_read), user: User = Depends(get_current_user)):
    return list((await db.execute(select(MitreTechnique))).scalars().all())


@router.get("/techniques/{technique_id}/drilldown", response_model=MitreDrilldownResponse)
async def technique_drilldown(
    technique_id: str,
    preset: str | None = ListParams.preset(),
    from_time: datetime | None = ListParams.from_time(),
    to_time: datetime | None = ListParams.to_time(),
    db: AsyncSession = Depends(get_db_read),
    user: User = Depends(get_current_user),
):
    tr = resolve_time_range(preset, from_time, to_time)
    return await get_technique_drilldown(db, tr, technique_id)


@router.get("/matrix")
async def get_matrix(
    preset: str | None = ListParams.preset(),
    from_time: datetime | None = ListParams.from_time(),
    to_time: datetime | None = ListParams.to_time(),
    db: AsyncSession = Depends(get_db_read),
    user: User = Depends(get_current_user),
):
    tr = resolve_time_range(preset, from_time, to_time)
    q = select(Event)
    for clause in apply_time_range(Event.timestamp, tr):
        q = q.where(clause)
    events = list((await db.execute(q.limit(10000))).scalars().all())
    techniques = get_matrix_summary(events)
    all_techniques = list((await db.execute(select(MitreTechnique))).scalars().all())
    for t in all_techniques:
        if t.technique_id not in techniques:
            techniques[t.technique_id] = {
                "technique_id": t.technique_id,
                "tactic": t.tactic,
                "name": t.name,
                "count": 0,
            }
    tactics = {}
    for t in techniques.values():
        tactics.setdefault(t["tactic"], []).append(t)
    detected = sum(1 for t in techniques.values() if t["count"] > 0)
    coverage_pct = round(detected / max(len(all_techniques), 1) * 100, 1)
    tactic_coverage = {}
    for tactic, items in tactics.items():
        with_events = sum(1 for i in items if i["count"] > 0)
        tactic_coverage[tactic] = round(with_events / max(len(items), 1) * 100, 1)
    return {
        "tactics": tactics,
        "techniques": list(techniques.values()),
        "coverage_pct": coverage_pct,
        "tactic_coverage": tactic_coverage,
        "total_techniques": len(all_techniques),
    }
