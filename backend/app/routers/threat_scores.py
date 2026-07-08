from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_read
from app.dependencies import get_current_user
from app.models.host import Host
from app.models.threat_score import HostThreatScore
from app.models.user import User

router = APIRouter(prefix="/threat-scores", tags=["threat-scores"])


class ScoreResponse(BaseModel):
    host_id: str
    host_name: str
    score: int
    health_score: int
    factors: dict


@router.get("")
async def ranked_scores(db: AsyncSession = Depends(get_db_read), user: User = Depends(get_current_user)):
    hosts = {h.id: h.name for h in (await db.execute(select(Host))).scalars().all()}
    scores = (await db.execute(select(HostThreatScore).order_by(HostThreatScore.score.desc()))).scalars().all()
    return [ScoreResponse(host_id=str(s.host_id), host_name=hosts.get(s.host_id, "?"), score=s.score, health_score=s.health_score, factors=s.factors or {}) for s in scores]
