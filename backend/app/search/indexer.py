"""Build OpenSearch documents from ORM models."""

from app.models.alert import Alert
from app.models.event import Event
from app.models.host import Host
from app.search.opensearch_client import index_document, index_event_doc


def event_to_doc(event: Event, host_name: str) -> dict:
    return {
        "id": str(event.id),
        "host_id": str(event.host_id),
        "host_name": host_name,
        "event_type": event.event_type,
        "severity": event.severity,
        "description": event.description,
        "raw_log": event.raw_log,
        "username": event.username,
        "source_ip": str(event.source_ip) if event.source_ip else None,
        "timestamp": event.timestamp.isoformat(),
    }


async def index_event(event: Event, host_name: str) -> None:
    await index_event_doc(event_to_doc(event, host_name))


async def index_alert(alert: Alert, host_name: str = "") -> None:
    await index_document(
        "securi-alerts",
        str(alert.id),
        {
            "id": str(alert.id),
            "host_id": str(alert.host_id),
            "host_name": host_name,
            "title": alert.title,
            "description": alert.description,
            "severity": alert.severity,
            "status": alert.status,
            "created_at": alert.created_at.isoformat(),
        },
    )


async def index_host(host: Host) -> None:
    await index_document(
        "securi-hosts",
        str(host.id),
        {
            "id": str(host.id),
            "name": host.name,
            "hostname": host.hostname,
            "status": host.status,
            "ip": str(host.ip_address) if host.ip_address else None,
        },
    )
