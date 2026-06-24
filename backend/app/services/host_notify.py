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
