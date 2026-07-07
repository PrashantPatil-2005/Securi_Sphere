from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.dashboard import DashboardLayoutResponse, DashboardLayoutUpdate
from app.services.dashboard_layout import get_dashboard_layout, update_dashboard_layout

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/layout", response_model=DashboardLayoutResponse)
async def read_layout(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await get_dashboard_layout(db, user)


@router.put("/layout", response_model=DashboardLayoutResponse)
async def write_layout(
    body: DashboardLayoutUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await update_dashboard_layout(db, user, body)
