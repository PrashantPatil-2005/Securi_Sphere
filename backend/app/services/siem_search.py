"""SIEM-style query parser: host:web01 severity:critical source_ip:ref:bad_ips"""
import re
from datetime import datetime

from sqlalchemy import false, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.event import Event
from app.models.host import Host
from app.services.reference_sets import resolve_ref_filters
from app.utils.query import TIME_PRESETS, resolve_time_range

FIELD_ALIASES = {
    "host": "host",
    "hostname": "host",
    "severity": "severity",
    "event_type": "event_type",
    "type": "event_type",
    "username": "username",
    "user": "username",
    "source_ip": "source_ip",
    "ip": "source_ip",
    "status": "status",
    "date": "date",
    "preset": "date",
}

DATE_ALIASES = {
    "today": "today",
    "last_24_hours": "24h",
    "last_24h": "24h",
    "24h": "24h",
    "last_7_days": "7d",
    "7d": "7d",
    "last_30_days": "30d",
    "30d": "30d",
    "last_90_days": "90d",
    "90d": "90d",
}

TOKEN_RE = re.compile(r'(\w+):("([^"]+)"|(\S+))')


def parse_siem_query(query: str) -> dict:
    filters: dict[str, str] = {}
    free_text: list[str] = []

    for match in TOKEN_RE.finditer(query):
        key = FIELD_ALIASES.get(match.group(1).lower(), match.group(1).lower())
        value = match.group(3) or match.group(4)
        filters[key] = value

    remainder = TOKEN_RE.sub("", query).strip()
    if remainder:
        free_text.append(remainder)

    preset = None
    from_time = None
    to_time = None
    if "date" in filters:
        date_val = filters.pop("date").lower().replace("-", "_")
        preset = DATE_ALIASES.get(date_val, date_val if date_val in TIME_PRESETS else None)

    return {
        "filters": filters,
        "free_text": " ".join(free_text),
        "preset": preset,
        "from_time": from_time,
        "to_time": to_time,
    }


async def execute_siem_search(
    db: AsyncSession,
    query: str,
    preset: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    limit: int = 50,
) -> dict:
    parsed = parse_siem_query(query)
    parsed = await resolve_ref_filters(db, parsed)
    tr = resolve_time_range(parsed.get("preset") or preset, from_time, to_time)

    from app.search.opensearch_client import siem_search_opensearch

    os_hits = await siem_search_opensearch(parsed, tr, limit=limit)
    if os_hits is not None:
        return {
            "parsed": parsed,
            "time_range": {
                "from": tr.from_time.isoformat() if tr.from_time else None,
                "to": tr.to_time.isoformat() if tr.to_time else None,
            },
            "backend": "opensearch",
            **os_hits,
        }

    host_name = parsed["filters"].get("host")
    host_id = None
    if host_name:
        host = (
            await db.execute(
                select(Host).where(or_(Host.name.ilike(host_name), Host.hostname.ilike(host_name))).limit(1)
            )
        ).scalar_one_or_none()
        if host:
            host_id = host.id

    event_clauses = []
    if tr.from_time:
        event_clauses.append(Event.timestamp >= tr.from_time)
    if tr.to_time:
        event_clauses.append(Event.timestamp <= tr.to_time)
    if host_id:
        event_clauses.append(Event.host_id == host_id)
    if "severity" in parsed["filters"]:
        event_clauses.append(Event.severity == parsed["filters"]["severity"])
    if "event_type" in parsed["filters"]:
        et = parsed["filters"]["event_type"]
        if et == "failed_login":
            et = "ssh_login_failure"
        event_clauses.append(Event.event_type == et)
    if "username" in parsed["filters"]:
        username_filter = parsed["filters"]["username"]
        event_clauses.append(
            or_(
                Event.username.ilike(username_filter),
                Event.metadata_["username"].astext.ilike(username_filter),
            )
        )
    elif "username" in parsed.get("in_filters", {}):
        values = parsed["in_filters"]["username"]
        if not values:
            event_clauses.append(false())
        else:
            event_clauses.append(
                or_(
                    Event.username.in_(values),
                    Event.metadata_["username"].astext.in_(values),
                )
            )
    if "source_ip" in parsed["filters"]:
        ip_filter = parsed["filters"]["source_ip"]
        event_clauses.append(
            or_(
                Event.source_ip == ip_filter,
                Event.metadata_["source_ip"].astext == ip_filter,
            )
        )
    elif "source_ip" in parsed.get("in_filters", {}):
        values = parsed["in_filters"]["source_ip"]
        if not values:
            event_clauses.append(false())
        else:
            event_clauses.append(
                or_(
                    Event.source_ip.in_(values),
                    Event.metadata_["source_ip"].astext.in_(values),
                )
            )
    if parsed["free_text"]:
        pattern = f"%{parsed['free_text']}%"
        event_clauses.append(
            or_(Event.description.ilike(pattern), Event.raw_log.ilike(pattern), Event.event_type.ilike(pattern))
        )

    events = list(
        (
            await db.execute(
                select(Event).where(*event_clauses).order_by(Event.timestamp.desc()).limit(limit)
            )
        ).scalars().all()
    )

    alert_clauses = []
    if tr.from_time:
        alert_clauses.append(Alert.created_at >= tr.from_time)
    if tr.to_time:
        alert_clauses.append(Alert.created_at <= tr.to_time)
    if host_id:
        alert_clauses.append(Alert.host_id == host_id)
    if "severity" in parsed["filters"]:
        alert_clauses.append(Alert.severity == parsed["filters"]["severity"])
    if "status" in parsed["filters"]:
        alert_clauses.append(Alert.status == parsed["filters"]["status"])

    alerts = list(
        (
            await db.execute(
                select(Alert).where(*alert_clauses).order_by(Alert.created_at.desc()).limit(limit)
            )
        ).scalars().all()
    )

    return {
        "parsed": parsed,
        "time_range": {
            "from": tr.from_time.isoformat() if tr.from_time else None,
            "to": tr.to_time.isoformat() if tr.to_time else None,
        },
        "backend": "postgres",
        "events": [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "severity": e.severity,
                "description": e.description,
                "timestamp": e.timestamp.isoformat(),
                "host_id": str(e.host_id),
            }
            for e in events
        ],
        "alerts": [
            {
                "id": str(a.id),
                "title": a.title,
                "severity": a.severity,
                "status": a.status,
                "created_at": a.created_at.isoformat(),
            }
            for a in alerts
        ],
        "total_events": len(events),
        "total_alerts": len(alerts),
    }
