from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.host import Host
from app.services.detection import create_alert


async def check_agent_integrity(
    db: AsyncSession,
    host: Host,
    agent_hash: str | None,
    agent_version: str | None,
) -> None:
    if agent_version:
        host.agent_version = agent_version

    if not agent_hash:
        return

    if host.agent_hash and host.agent_hash != agent_hash:
        host.agent_hash_changed_at = datetime.now(timezone.utc)
        await create_alert(
            db,
            host.id,
            "Agent Configuration Modified",
            f"Agent hash changed on host {host.name}. Possible tampering.",
            "critical",
            None,
        )
    host.agent_hash = agent_hash
