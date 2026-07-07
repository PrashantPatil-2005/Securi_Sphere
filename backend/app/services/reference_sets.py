"""Reference set lookups and SIEM ref: expansion."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.reference import REFERENCE_SET_TYPES, ReferenceSet, ReferenceSetEntry

REF_PREFIX = "ref:"


def is_ref_filter(value: str) -> bool:
    return value.startswith(REF_PREFIX)


def ref_set_name(value: str) -> str:
    return value[len(REF_PREFIX) :]


async def get_set_by_name(db: AsyncSession, name: str) -> ReferenceSet | None:
    return (
        await db.execute(
            select(ReferenceSet)
            .options(selectinload(ReferenceSet.entries))
            .where(ReferenceSet.name == name, ReferenceSet.enabled.is_(True))
        )
    ).scalar_one_or_none()


async def get_set_values(db: AsyncSession, name: str) -> list[str]:
    ref_set = await get_set_by_name(db, name)
    if not ref_set:
        return []
    return [e.value for e in ref_set.entries]


async def resolve_ref_filters(db: AsyncSession, parsed: dict) -> dict:
    """Expand ref:setname filters into in_filters lists."""
    filters: dict[str, str] = {}
    in_filters: dict[str, list[str]] = {}
    for key, value in parsed.get("filters", {}).items():
        if is_ref_filter(value):
            in_filters[key] = await get_set_values(db, ref_set_name(value))
        else:
            filters[key] = value
    parsed = dict(parsed)
    parsed["filters"] = filters
    parsed["in_filters"] = in_filters
    return parsed


async def lookup_value(db: AsyncSession, *, set_type: str | None, value: str) -> list[dict]:
    """Return reference sets that contain this value."""
    q = (
        select(ReferenceSet, ReferenceSetEntry)
        .join(ReferenceSetEntry, ReferenceSetEntry.set_id == ReferenceSet.id)
        .where(ReferenceSet.enabled.is_(True), ReferenceSetEntry.value == value)
    )
    if set_type:
        q = q.where(ReferenceSet.set_type == set_type)
    rows = (await db.execute(q)).all()
    return [
        {"set_id": str(rs.id), "set_name": rs.name, "set_type": rs.set_type, "note": entry.note}
        for rs, entry in rows
    ]


def validate_set_type(set_type: str) -> str:
    if set_type not in REFERENCE_SET_TYPES:
        raise ValueError(f"set_type must be one of: {', '.join(sorted(REFERENCE_SET_TYPES))}")
    return set_type
