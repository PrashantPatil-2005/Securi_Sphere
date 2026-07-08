"""Reference sets API — QRadar-style indicator lists."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import require_roles
from app.models.reference import ReferenceSet, ReferenceSetEntry
from app.models.user import User
from app.schemas.reference import (
    ReferenceLookupResponse,
    ReferenceSetCreate,
    ReferenceSetEntriesBulk,
    ReferenceSetEntryResponse,
    ReferenceSetResponse,
    ReferenceSetUpdate,
)
from app.services.audit import log_audit
from app.services.reference_sets import lookup_value, validate_set_type
from app.services.threat_intel_feeds import sync_reference_set_feed

router = APIRouter(prefix="/reference-sets", tags=["reference-sets"])
VALID_SOURCE_TYPES = {"manual", "feed"}


def _validate_feed_fields(*, source_type: str, feed_url: str | None, feed_format: str | None) -> None:
    if source_type == "feed" and not (feed_url or "").strip():
        raise HTTPException(status_code=400, detail="feed_url is required for source_type=feed")
    if source_type != "feed" and (feed_url or feed_format):
        raise HTTPException(status_code=400, detail="feed_url/feed_format are only valid for source_type=feed")


def _set_response(rs: ReferenceSet, entry_count: int | None = None) -> ReferenceSetResponse:
    return ReferenceSetResponse(
        id=rs.id,
        name=rs.name,
        description=rs.description,
        set_type=rs.set_type,
        enabled=rs.enabled,
        source_type=rs.source_type,
        feed_url=rs.feed_url,
        feed_format=rs.feed_format,
        feed_last_sync_at=rs.feed_last_sync_at,
        feed_last_sync_status=rs.feed_last_sync_status,
        feed_last_sync_error=rs.feed_last_sync_error,
        entry_count=entry_count if entry_count is not None else len(rs.entries),
        created_at=rs.created_at,
    )


@router.get("", response_model=list[ReferenceSetResponse])
async def list_reference_sets(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst", "viewer")),
):
    rows = list(
        (
            await db.execute(
                select(ReferenceSet, func.count(ReferenceSetEntry.id))
                .outerjoin(ReferenceSetEntry, ReferenceSetEntry.set_id == ReferenceSet.id)
                .group_by(ReferenceSet.id)
                .order_by(ReferenceSet.name)
            )
        ).all()
    )
    return [_set_response(rs, int(count)) for rs, count in rows]


@router.post("", response_model=ReferenceSetResponse, status_code=201)
async def create_reference_set(
    body: ReferenceSetCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst")),
):
    if body.source_type not in VALID_SOURCE_TYPES:
        raise HTTPException(status_code=400, detail=f"source_type must be one of {sorted(VALID_SOURCE_TYPES)}")
    _validate_feed_fields(source_type=body.source_type, feed_url=body.feed_url, feed_format=body.feed_format)
    try:
        validate_set_type(body.set_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    existing = (
        await db.execute(select(ReferenceSet).where(ReferenceSet.name == body.name))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Reference set name already exists")

    rs = ReferenceSet(
        name=body.name.strip(),
        description=body.description,
        set_type=body.set_type,
        enabled=body.enabled,
        source_type=body.source_type,
        feed_url=(body.feed_url or "").strip() or None,
        feed_format=body.feed_format,
    )
    db.add(rs)
    await db.flush()
    await log_audit(db, "reference_set_created", user_id=user.id, details={"name": rs.name})
    return _set_response(rs, 0)


@router.get("/lookup", response_model=ReferenceLookupResponse)
async def reference_lookup(
    value: str = Query(..., min_length=1),
    set_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst", "viewer")),
):
    if set_type:
        try:
            validate_set_type(set_type)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    matches = await lookup_value(db, set_type=set_type, value=value.strip())
    return ReferenceLookupResponse(value=value, matches=matches)


@router.get("/{set_id}", response_model=ReferenceSetResponse)
async def get_reference_set(
    set_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst", "viewer")),
):
    rs = (
        await db.execute(
            select(ReferenceSet).options(selectinload(ReferenceSet.entries)).where(ReferenceSet.id == set_id)
        )
    ).scalar_one_or_none()
    if not rs:
        raise HTTPException(status_code=404, detail="Reference set not found")
    return _set_response(rs)


@router.get("/{set_id}/entries", response_model=list[ReferenceSetEntryResponse])
async def list_entries(
    set_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst", "viewer")),
):
    rs = (await db.execute(select(ReferenceSet).where(ReferenceSet.id == set_id))).scalar_one_or_none()
    if not rs:
        raise HTTPException(status_code=404, detail="Reference set not found")
    entries = list(
        (
            await db.execute(
                select(ReferenceSetEntry)
                .where(ReferenceSetEntry.set_id == set_id)
                .order_by(ReferenceSetEntry.value)
            )
        ).scalars().all()
    )
    return entries


@router.patch("/{set_id}", response_model=ReferenceSetResponse)
async def update_reference_set(
    set_id: UUID,
    body: ReferenceSetUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst")),
):
    rs = (
        await db.execute(
            select(ReferenceSet).options(selectinload(ReferenceSet.entries)).where(ReferenceSet.id == set_id)
        )
    ).scalar_one_or_none()
    if not rs:
        raise HTTPException(status_code=404, detail="Reference set not found")
    if body.description is not None:
        rs.description = body.description
    if body.enabled is not None:
        rs.enabled = body.enabled
    if body.source_type is not None:
        if body.source_type not in VALID_SOURCE_TYPES:
            raise HTTPException(status_code=400, detail=f"source_type must be one of {sorted(VALID_SOURCE_TYPES)}")
        rs.source_type = body.source_type
        if body.source_type == "manual":
            rs.feed_url = None
            rs.feed_format = None
    if body.feed_url is not None:
        rs.feed_url = (body.feed_url or "").strip() or None
    if body.feed_format is not None:
        rs.feed_format = body.feed_format
    _validate_feed_fields(source_type=rs.source_type, feed_url=rs.feed_url, feed_format=rs.feed_format)
    await db.flush()
    return _set_response(rs)


@router.post("/{set_id}/sync-feed")
async def sync_feed(
    set_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst")),
):
    rs = (await db.execute(select(ReferenceSet).where(ReferenceSet.id == set_id))).scalar_one_or_none()
    if not rs:
        raise HTTPException(status_code=404, detail="Reference set not found")
    if rs.source_type != "feed":
        raise HTTPException(status_code=400, detail="Reference set is not feed-backed")
    try:
        result = await sync_reference_set_feed(db, rs)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Feed sync failed: {exc}") from exc
    await log_audit(
        db,
        "reference_set_feed_sync",
        user_id=user.id,
        details={"set_id": str(rs.id), "set_name": rs.name, **result},
    )
    return {"set_id": str(rs.id), **result}


@router.post("/{set_id}/entries", response_model=list[ReferenceSetEntryResponse])
async def add_entries(
    set_id: UUID,
    body: ReferenceSetEntriesBulk,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst")),
):
    rs = (await db.execute(select(ReferenceSet).where(ReferenceSet.id == set_id))).scalar_one_or_none()
    if not rs:
        raise HTTPException(status_code=404, detail="Reference set not found")

    existing = set(
        (await db.execute(select(ReferenceSetEntry.value).where(ReferenceSetEntry.set_id == set_id))).scalars().all()
    )
    added: list[ReferenceSetEntry] = []
    for raw in body.values:
        val = raw.strip()
        if not val or val in existing:
            continue
        entry = ReferenceSetEntry(set_id=set_id, value=val, note=body.note)
        db.add(entry)
        added.append(entry)
        existing.add(val)
    await db.flush()
    await log_audit(db, "reference_set_entries_added", user_id=user.id, details={"set": rs.name, "count": len(added)})
    return added


@router.delete("/{set_id}/entries/{entry_id}", status_code=204)
async def delete_entry(
    set_id: UUID,
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst")),
):
    entry = (
        await db.execute(
            select(ReferenceSetEntry).where(
                ReferenceSetEntry.id == entry_id, ReferenceSetEntry.set_id == set_id
            )
        )
    ).scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    await db.delete(entry)


@router.delete("/{set_id}", status_code=204)
async def delete_reference_set(
    set_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    rs = (await db.execute(select(ReferenceSet).where(ReferenceSet.id == set_id))).scalar_one_or_none()
    if not rs:
        raise HTTPException(status_code=404, detail="Reference set not found")
    await db.delete(rs)
    await log_audit(db, "reference_set_deleted", user_id=user.id, details={"name": rs.name})
