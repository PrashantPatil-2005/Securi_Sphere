from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.host import Host
from app.models.threat_score import HostThreatScore
from app.models.user import User
from app.config import settings

router = APIRouter(prefix="/network", tags=["network"])


@router.get("/topology")
async def topology(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    hosts = list((await db.execute(select(Host))).scalars().all())
    scores = {s.host_id: s.score for s in (await db.execute(select(HostThreatScore))).scalars().all()}
    nodes = [{"id": "server", "label": "Securi Server", "type": "server", "status": "online"}]
    edges = []
    for h in hosts:
        nodes.append({
            "id": str(h.id), "label": h.name, "type": "host", "status": h.status,
            "threat_score": scores.get(h.id, 0), "ip": str(h.ip_address) if h.ip_address else None,
        })
        edges.append({"from": "server", "to": str(h.id)})
    return {"nodes": nodes, "edges": edges}
