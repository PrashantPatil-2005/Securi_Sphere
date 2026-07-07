from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.investigation import InvestigationWorkspaceResponse
from app.services.investigation_workspace import build_investigation_workspace

router = APIRouter(prefix="/investigation", tags=["investigation"])


@router.get("/workspace", response_model=InvestigationWorkspaceResponse)
async def get_investigation_workspace(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    alert_id: UUID | None = Query(None),
    offense_id: UUID | None = Query(None),
    incident_id: UUID | None = Query(None),
):
    return await build_investigation_workspace(
        db,
        alert_id=alert_id,
        offense_id=offense_id,
        incident_id=incident_id,
    )
