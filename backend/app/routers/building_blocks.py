"""Building blocks API — reusable SIEM query templates."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_roles
from app.models.reference import BuildingBlock
from app.models.user import User
from app.schemas.reference import BuildingBlockCreate, BuildingBlockResponse, BuildingBlockUpdate
from app.services.audit import log_audit

router = APIRouter(prefix="/building-blocks", tags=["building-blocks"])


@router.get("", response_model=list[BuildingBlockResponse])
async def list_building_blocks(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst", "viewer")),
):
    rows = list(
        (await db.execute(select(BuildingBlock).order_by(BuildingBlock.category, BuildingBlock.name))).scalars().all()
    )
    return rows


@router.post("", response_model=BuildingBlockResponse, status_code=201)
async def create_building_block(
    body: BuildingBlockCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst")),
):
    existing = (
        await db.execute(select(BuildingBlock).where(BuildingBlock.name == body.name))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Building block name already exists")

    block = BuildingBlock(
        name=body.name.strip(),
        description=body.description,
        category=body.category,
        siem_query=body.siem_query.strip(),
        enabled=body.enabled,
    )
    db.add(block)
    await db.flush()
    await log_audit(db, "building_block_created", user_id=user.id, details={"name": block.name})
    return block


@router.patch("/{block_id}", response_model=BuildingBlockResponse)
async def update_building_block(
    block_id: UUID,
    body: BuildingBlockUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst")),
):
    block = (await db.execute(select(BuildingBlock).where(BuildingBlock.id == block_id))).scalar_one_or_none()
    if not block:
        raise HTTPException(status_code=404, detail="Building block not found")
    if body.description is not None:
        block.description = body.description
    if body.category is not None:
        block.category = body.category
    if body.siem_query is not None:
        block.siem_query = body.siem_query.strip()
    if body.enabled is not None:
        block.enabled = body.enabled
    await db.flush()
    return block


@router.delete("/{block_id}", status_code=204)
async def delete_building_block(
    block_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    block = (await db.execute(select(BuildingBlock).where(BuildingBlock.id == block_id))).scalar_one_or_none()
    if not block:
        raise HTTPException(status_code=404, detail="Building block not found")
    await db.delete(block)
    await log_audit(db, "building_block_deleted", user_id=user.id, details={"name": block.name})
