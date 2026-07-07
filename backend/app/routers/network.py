"""Network host map — server hub plus flow-derived edges when available."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.event import Event
from app.models.host import Host
from app.models.threat_score import HostThreatScore
from app.models.user import User

router = APIRouter(prefix="/network", tags=["network"])


@router.get("/topology")
async def topology(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    hosts = list((await db.execute(select(Host))).scalars().all())
    scores = {s.host_id: s.score for s in (await db.execute(select(HostThreatScore))).scalars().all()}
    ip_to_host: dict[str, str] = {}
    for h in hosts:
        if h.ip_address:
            ip_to_host[str(h.ip_address)] = str(h.id)

    nodes = [{"id": "server", "label": "Securi Server", "type": "server", "status": "online"}]
    for h in hosts:
        nodes.append({
            "id": str(h.id), "label": h.name, "type": "host", "status": h.status,
            "threat_score": scores.get(h.id, 0), "ip": str(h.ip_address) if h.ip_address else None,
        })

    edges: list[dict[str, str]] = []
    seen_edges: set[tuple[str, str]] = set()

    flow_events = list(
        (
            await db.execute(
                select(Event)
                .where(Event.event_type == "network_flow")
                .order_by(Event.timestamp.desc())
                .limit(500)
            )
        ).scalars().all()
    )
    for ev in flow_events:
        meta = ev.metadata_ or {}
        src_ip = meta.get("src_ip")
        dst_ip = meta.get("dst_ip")
        src_id = ip_to_host.get(str(src_ip)) if src_ip else str(ev.host_id)
        dst_id = ip_to_host.get(str(dst_ip)) if dst_ip else None
        if src_id and dst_id and src_id != dst_id:
            key = (src_id, dst_id)
            if key not in seen_edges:
                seen_edges.add(key)
                edges.append({"from": src_id, "to": dst_id})

    if not edges:
        for h in hosts:
            edges.append({"from": "server", "to": str(h.id)})

    return {"nodes": nodes, "edges": edges}
