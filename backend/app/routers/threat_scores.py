from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_read
from app.dependencies import get_current_user
from app.models.host import Host
from app.models.threat_score import HostThreatScore
from app.models.user import User
from app.schemas.threat_score import ScoreResponse

router = APIRouter(prefix="/threat-scores", tags=["threat-scores"])


@router.get("")
async def ranked_scores(db: AsyncSession = Depends(get_db_read), user: User = Depends(get_current_user)):
    hosts = {h.id: h.name for h in (await db.execute(select(Host).limit(5000))).scalars().all()}
    scores = (await db.execute(select(HostThreatScore).order_by(HostThreatScore.score.desc()))).scalars().all()
    return [ScoreResponse(host_id=str(s.host_id), host_name=hosts.get(s.host_id, "?"), score=s.score, health_score=s.health_score, factors=s.factors or {}) for s in scores]
