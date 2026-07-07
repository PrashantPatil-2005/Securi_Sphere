"""Real-time reference set matching during event ingestion."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.event import Event
from app.models.host import Host
from app.models.reference import ReferenceSet

SET_TYPE_FIELDS: dict[str, list[str]] = {
    "ip": ["source_ip"],
    "username": ["username"],
    "hostname": ["hostname"],
    "domain": ["domain"],
    "hash": ["hash", "file_hash"],
    "port": ["port", "dest_port"],
}


def _event_field_values(event: Event, host: Host, field: str) -> list[str]:
    if field == "source_ip" and event.source_ip:
        return [str(event.source_ip)]
    if field == "username" and event.username:
        return [event.username]
    if field == "hostname":
        values: list[str] = []
        if host.hostname:
            values.append(host.hostname)
        if host.name:
            values.append(host.name)
        return values
    meta = event.metadata_ or {}
    if field in meta and meta[field] is not None:
        return [str(meta[field])]
    normalized = event.normalized_event or {}
    if field in normalized and normalized[field] is not None:
        return [str(normalized[field])]
    return []


async def check_reference_intel_on_event(db: AsyncSession, host: Host, event: Event) -> None:
    """Create alerts when event fields match enabled reference set entries."""
    sets = list(
        (
            await db.execute(
                select(ReferenceSet)
                .options(selectinload(ReferenceSet.entries))
                .where(ReferenceSet.enabled.is_(True))
            )
        ).scalars().all()
    )
    if not sets:
        return

    from app.services.detection import create_alert

    matches: list[tuple[str, str, str]] = []
    for ref_set in sets:
        entry_values = {e.value for e in ref_set.entries}
        if not entry_values:
            continue
        for field in SET_TYPE_FIELDS.get(ref_set.set_type, []):
            for value in _event_field_values(event, host, field):
                if value in entry_values:
                    matches.append((ref_set.name, field, value))
                    break

    if not matches:
        return

    if event.metadata_ is None:
        event.metadata_ = {}
    event.metadata_["intel_matches"] = [
        {"set_name": name, "field": field, "value": value} for name, field, value in matches
    ]

    for set_name, field, value in matches:
        await create_alert(
            db,
            host.id,
            f"Threat Intel Match: {set_name}",
            f"{field} {value} matched reference set '{set_name}'",
            "high",
            None,
        )
