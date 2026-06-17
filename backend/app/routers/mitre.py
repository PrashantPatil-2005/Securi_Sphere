from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.event import Event
from app.models.mitre import MitreTechnique
from app.models.user import User
from app.services.mitre import get_matrix_summary

router = APIRouter(prefix="/mitre", tags=["mitre"])


class TechniqueResponse(BaseModel):
    technique_id: str
    tactic: str
    name: str
    description: str | None
    model_config = {"from_attributes": True}


@router.get("/techniques", response_model=list[TechniqueResponse])
async def list_techniques(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return list((await db.execute(select(MitreTechnique))).scalars().all())


@router.get("/matrix")
async def get_matrix(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    events = list((await db.execute(select(Event).limit(5000))).scalars().all())
    techniques = get_matrix_summary(events)
    tactics = {}
    for t in techniques.values():
        tactics.setdefault(t["tactic"], []).append(t)
    return {"tactics": tactics, "techniques": list(techniques.values())}
