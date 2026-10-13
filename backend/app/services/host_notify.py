"""Broadcast host lifecycle events to connected dashboards."""

from app.models.host import Host
from app.websocket.manager import ws_manager


async def broadcast_host_update(host: Host, event: str = "host_status") -> None:
    await ws_manager.broadcast({
        "type": event,
        "data": {
            "id": str(host.id),
            "name": host.name,
            "status": host.status,
            "enrolled": bool(host.api_key_hash),
            "hostname": host.hostname,
            "last_seen": host.last_seen.isoformat() if host.last_seen else None,
        },
    })


async def is_host_in_maintenance(db, host_id) -> bool:
    """Check whether a host is in maintenance mode.

    Returns True if the host should be skipped for correlation/detection.
    Currently checks the host's status field; a status other than 'online'
    indicates the host is unavailable (e.g. maintenance, offline, draining).
    """
    from sqlalchemy import select
    from app.models.host import Host

    result = await db.execute(select(Host).where(Host.id == host_id))
    host = result.scalar_one_or_none()
    if not host:
        return True
    # Host is in maintenance if status is not "online"
    return host.status != "online"
