"""Seed demo reference sets and building blocks."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reference import BuildingBlock, ReferenceSet, ReferenceSetEntry


async def seed_reference_intel(db: AsyncSession) -> None:
    count = (await db.execute(select(func.count()).select_from(ReferenceSet))).scalar_one()
    if count > 0:
        return

    bad_ips = ReferenceSet(
        name="bad_ips",
        description="Known malicious or watchlist IP addresses",
        set_type="ip",
    )
    priv_users = ReferenceSet(
        name="privileged_users",
        description="Privileged accounts to monitor closely",
        set_type="username",
    )
    db.add(bad_ips)
    db.add(priv_users)
    await db.flush()

    for ip in ("203.0.113.50", "198.51.100.99", "192.0.2.100"):
        db.add(ReferenceSetEntry(set_id=bad_ips.id, value=ip, note="Demo watchlist"))
    for user in ("root", "admin", "svc_backup"):
        db.add(ReferenceSetEntry(set_id=priv_users.id, value=user, note="Privileged"))

    blocks = [
        BuildingBlock(
            name="Failed logins from bad IPs",
            description="SSH failures where source is in bad_ips reference set",
            category="threat_intel",
            siem_query="event_type:failed_login source_ip:ref:bad_ips date:24h",
        ),
        BuildingBlock(
            name="Privileged user activity",
            description="Events involving privileged accounts",
            category="compliance",
            siem_query="username:ref:privileged_users date:7d",
        ),
    ]
    for block in blocks:
        db.add(block)
