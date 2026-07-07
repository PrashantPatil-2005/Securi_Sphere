from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.siem import SavedSearch
from app.models.user import User
from app.schemas.dashboard import DashboardLayoutResponse
from app.schemas.saved_search import SavedSearchCreate, SavedSearchResponse, SavedSearchUpdate
from app.services.dashboard_layout import pin_saved_search_widget

router = APIRouter(prefix="/saved-searches", tags=["saved-searches"])


def _to_response(row: SavedSearch) -> SavedSearchResponse:
    return SavedSearchResponse(
        id=row.id,
        name=row.name,
        query=row.query,
        alert_enabled=row.alert_enabled,
        interval_minutes=row.interval_minutes,
        created_at=row.created_at,
    )


@router.get("", response_model=list[SavedSearchResponse])
async def list_saved_searches(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = (
        await db.execute(
            select(SavedSearch).where(SavedSearch.user_id == user.id).order_by(SavedSearch.created_at.desc())
        )
    ).scalars().all()
    return [_to_response(r) for r in rows]


@router.post("", response_model=SavedSearchResponse)
async def create_saved_search(
    body: SavedSearchCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = SavedSearch(
        user_id=user.id,
        name=body.name.strip(),
        query=body.query.strip(),
        alert_enabled=body.alert_enabled,
        interval_minutes=body.interval_minutes,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _to_response(row)


@router.patch("/{search_id}", response_model=SavedSearchResponse)
async def update_saved_search(
    search_id: UUID,
    body: SavedSearchUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = (
        await db.execute(
            select(SavedSearch).where(SavedSearch.id == search_id, SavedSearch.user_id == user.id)
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Saved search not found")
    if body.name is not None:
        row.name = body.name.strip()
    if body.query is not None:
        row.query = body.query.strip()
    if body.alert_enabled is not None:
        row.alert_enabled = body.alert_enabled
    if body.interval_minutes is not None:
        row.interval_minutes = body.interval_minutes
    await db.commit()
    await db.refresh(row)
    return _to_response(row)


@router.delete("/{search_id}")
async def delete_saved_search(
    search_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = (
        await db.execute(
            select(SavedSearch).where(SavedSearch.id == search_id, SavedSearch.user_id == user.id)
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Saved search not found")
    await db.delete(row)
    await db.commit()
    return {"ok": True}


@router.post("/{search_id}/pin-dashboard", response_model=DashboardLayoutResponse)
async def pin_saved_search_to_dashboard(
    search_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = (
        await db.execute(
            select(SavedSearch).where(SavedSearch.id == search_id, SavedSearch.user_id == user.id)
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Saved search not found")
    return await pin_saved_search_widget(db, user, search_id)
