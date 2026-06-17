from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.alert import Alert
from app.models.event import Event
from app.models.host import Host
from app.models.user import User
from app.schemas.search import SearchResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def global_search(
    q: str = Query(min_length=1),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pattern = f"%{q}%"
    hosts = (await db.execute(
        select(Host).where(
            or_(Host.name.ilike(pattern), Host.hostname.ilike(pattern), Host.ip_address.cast(str).ilike(pattern))
        ).limit(20)
    )).scalars().all()

    alerts = (await db.execute(
        select(Alert).where(or_(Alert.title.ilike(pattern), Alert.description.ilike(pattern))).limit(20)
    )).scalars().all()

    events = (await db.execute(
        select(Event).where(or_(Event.description.ilike(pattern), Event.raw_log.ilike(pattern))).limit(20)
    )).scalars().all()

    return SearchResponse(hosts=list(hosts), alerts=list(alerts), events=list(events), query=q)
