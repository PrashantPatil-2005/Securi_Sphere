"""Build OpenSearch documents from ORM models."""

from app.models.alert import Alert
from app.models.event import Event
from app.models.host import Host
from app.search.index_names import ALERTS_INDEX, HOSTS_INDEX
from app.search.opensearch_client import bulk_index_documents, bulk_index_event_docs, index_document


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
    from app.search.opensearch_client import index_event_doc

    await index_event_doc(event_to_doc(event, host_name))


async def index_events_batch(events: list[Event], host_names: dict) -> int:
    """Bulk index a batch of events after ingest."""
    docs = [event_to_doc(e, host_names.get(e.host_id, "?")) for e in events]
    return await bulk_index_event_docs(docs)


async def index_alert(alert: Alert, host_name: str = "") -> None:
    await index_document(
        ALERTS_INDEX,
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


async def index_alerts_batch(alerts: list[Alert], host_names: dict) -> int:
    pairs = [
        (
            str(a.id),
            {
                "id": str(a.id),
                "host_id": str(a.host_id),
                "host_name": host_names.get(a.host_id, ""),
                "title": a.title,
                "description": a.description,
                "severity": a.severity,
                "status": a.status,
                "created_at": a.created_at.isoformat(),
            },
        )
        for a in alerts
    ]
    return await bulk_index_documents(ALERTS_INDEX, pairs)


async def index_host(host: Host) -> None:
    await index_document(
        HOSTS_INDEX,
        str(host.id),
        {
            "id": str(host.id),
            "name": host.name,
            "hostname": host.hostname,
            "status": host.status,
            "ip": str(host.ip_address) if host.ip_address else None,
        },
    )


async def index_hosts_batch(hosts: list[Host]) -> int:
    pairs = [
        (
            str(h.id),
            {
                "id": str(h.id),
                "name": h.name,
                "hostname": h.hostname,
                "status": h.status,
                "ip": str(h.ip_address) if h.ip_address else None,
            },
        )
        for h in hosts
    ]
    return await bulk_index_documents(HOSTS_INDEX, pairs)
