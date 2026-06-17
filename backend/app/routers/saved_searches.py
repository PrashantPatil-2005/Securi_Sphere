from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.siem import SavedSearch
from app.models.user import User

router = APIRouter(prefix="/saved-searches", tags=["saved-searches"])


class SavedSearchCreate(BaseModel):
    name: str
    query: str


@router.get("")
async def list_saved_searches(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = (
        await db.execute(
            select(SavedSearch).where(SavedSearch.user_id == user.id).order_by(SavedSearch.created_at.desc())
        )
    ).scalars().all()
    return [
        {"id": str(r.id), "name": r.name, "query": r.query, "created_at": r.created_at.isoformat()}
        for r in rows
    ]


@router.post("")
async def create_saved_search(
    body: SavedSearchCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = SavedSearch(user_id=user.id, name=body.name, query=body.query)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {"id": str(row.id), "name": row.name, "query": row.query}


@router.delete("/{search_id}")
async def delete_saved_search(
    search_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from fastapi import HTTPException

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
