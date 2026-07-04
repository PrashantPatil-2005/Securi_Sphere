"""Build filtered queries for list and export endpoints."""
from uuid import UUID

from sqlalchemy import String, and_, cast, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.alert_rule import AlertRule
from app.models.event import Event
from app.models.host import Host
from app.models.threat_score import HostThreatScore
from app.models.user import User
from app.utils.cursor import decode_event_cursor, encode_event_cursor
from app.utils.query import SEVERITY_ORDER, SortOrder, TimeRange, apply_time_range
from app.utils.simulation_filter import real_events_only, should_exclude_simulated


def _severity_case(column):
    from sqlalchemy import case

    return case(
        *[(column == k, v) for k, v in SEVERITY_ORDER.items()],
        else_=0,
    )


async def query_events(
    db: AsyncSession,
    tr: TimeRange,
    *,
    host_id: UUID | None = None,
    severity: str | None = None,
    event_type: str | None = None,
    username: str | None = None,
    source_ip: str | None = None,
    service_name: str | None = None,
    status: str | None = None,
    q: str | None = None,
    exact: bool = False,
    sort: SortOrder = SortOrder.newest,
    page: int = 1,
    page_size: int = 50,
    cursor: str | None = None,
    count_only: bool = False,
    include_simulated: bool | None = None,
):
    query = select(Event)
    count_q = select(func.count()).select_from(Event)
    clauses = list(apply_time_range(Event.timestamp, tr))
    if should_exclude_simulated(include_simulated):
        clauses.append(real_events_only())

    if host_id:
        clauses.append(Event.host_id == host_id)
    if severity:
        clauses.append(Event.severity == severity)
    if event_type:
        clauses.append(Event.event_type == event_type)
    if username:
        clauses.append(Event.metadata_["username"].astext.ilike(username if exact else f"%{username}%"))
    if source_ip:
        ip_clause = or_(
            Event.metadata_["source_ip"].astext.ilike(source_ip if exact else f"%{source_ip}%"),
            Event.metadata_["ip"].astext.ilike(source_ip if exact else f"%{source_ip}%"),
        )
        clauses.append(ip_clause)
    if service_name:
        clauses.append(
            or_(
                Event.metadata_["service"].astext.ilike(f"%{service_name}%"),
                Event.event_type.ilike(f"%{service_name}%"),
            )
        )
    if status:
        clauses.append(Event.metadata_["status"].astext.ilike(status if exact else f"%{status}%"))
    if q:
        if exact:
            clauses.append(
                or_(
                    Event.description == q,
                    Event.event_type == q,
                    Event.raw_log == q,
                )
            )
        else:
            pattern = f"%{q}%"
            clauses.append(
                or_(
                    Event.description.ilike(pattern),
                    Event.raw_log.ilike(pattern),
                    Event.event_type.ilike(pattern),
                    cast(Event.metadata_, String).ilike(pattern),
                )
            )

    for c in clauses:
        query = query.where(c)
        count_q = count_q.where(c)

    total = (await db.execute(count_q)).scalar_one()
    if count_only:
        return [], total, None, False

    if sort == SortOrder.oldest:
        query = query.order_by(Event.timestamp.asc(), Event.id.asc())
    elif sort == SortOrder.severity:
        query = query.order_by(_severity_case(Event.severity).desc(), Event.timestamp.desc(), Event.id.desc())
    else:
        query = query.order_by(Event.timestamp.desc(), Event.id.desc())

    if cursor:
        try:
            cursor_ts, cursor_id, cursor_sev = decode_event_cursor(cursor)
        except (ValueError, KeyError, TypeError):
            return [], total, None, False
        if sort == SortOrder.oldest:
            query = query.where(
                or_(
                    Event.timestamp > cursor_ts,
                    and_(Event.timestamp == cursor_ts, Event.id > cursor_id),
                )
            )
        elif sort == SortOrder.severity and cursor_sev is not None:
            sev = _severity_case(Event.severity)
            query = query.where(
                or_(
                    sev < cursor_sev,
                    and_(sev == cursor_sev, Event.timestamp < cursor_ts),
                    and_(sev == cursor_sev, Event.timestamp == cursor_ts, Event.id < cursor_id),
                )
            )
        else:
            query = query.where(
                or_(
                    Event.timestamp < cursor_ts,
                    and_(Event.timestamp == cursor_ts, Event.id < cursor_id),
                )
            )
        fetch_limit = page_size + 1
        result = await db.execute(query.limit(fetch_limit))
    elif page > 1:
        fetch_limit = page_size + 1
        result = await db.execute(query.offset((page - 1) * page_size).limit(fetch_limit))
    else:
        fetch_limit = page_size + 1
        result = await db.execute(query.limit(fetch_limit))

    items = list(result.scalars().all())
    has_more = len(items) > page_size
    if has_more:
        items = items[:page_size]

    next_cursor = None
    if items and has_more:
        last = items[-1]
        severity_rank = SEVERITY_ORDER.get(last.severity, 0) if sort == SortOrder.severity else None
        next_cursor = encode_event_cursor(
            timestamp=last.timestamp,
            event_id=last.id,
            severity_rank=severity_rank,
        )

    return items, total, next_cursor, has_more


async def query_alerts(
    db: AsyncSession,
    tr: TimeRange,
    *,
    host_id: UUID | None = None,
    severity: str | None = None,
    status: str | None = None,
    rule_name: str | None = None,
    assigned_to: UUID | None = None,
    q: str | None = None,
    exact: bool = False,
    sort: SortOrder = SortOrder.newest,
    page: int = 1,
    page_size: int = 50,
):
    query = select(Alert).outerjoin(AlertRule, Alert.rule_id == AlertRule.id)
    count_q = select(func.count()).select_from(Alert).outerjoin(AlertRule, Alert.rule_id == AlertRule.id)
    clauses = apply_time_range(Alert.created_at, tr)

    if host_id:
        clauses.append(Alert.host_id == host_id)
    if severity:
        clauses.append(Alert.severity == severity)
    if status:
        clauses.append(Alert.status == status)
    if assigned_to:
        clauses.append(Alert.assigned_to == assigned_to)
    if rule_name:
        clauses.append(AlertRule.name.ilike(f"%{rule_name}%"))
    if q:
        if exact:
            clauses.append(or_(Alert.title == q, Alert.description == q))
        else:
            pattern = f"%{q}%"
            clauses.append(or_(Alert.title.ilike(pattern), Alert.description.ilike(pattern)))

    for c in clauses:
        query = query.where(c)
        count_q = count_q.where(c)

    total = (await db.execute(count_q)).scalar_one()

    if sort == SortOrder.oldest:
        query = query.order_by(Alert.created_at.asc())
    elif sort == SortOrder.severity:
        query = query.order_by(_severity_case(Alert.severity).desc(), Alert.created_at.desc())
    elif sort == SortOrder.host_name:
        query = query.join(Host, Alert.host_id == Host.id).order_by(Host.name.asc())
    else:
        query = query.order_by(Alert.created_at.desc())

    result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    return list(result.scalars().unique().all()), total


async def query_hosts(
    db: AsyncSession,
    *,
    hostname: str | None = None,
    status: str | None = None,
    os_info: str | None = None,
    min_risk: int | None = None,
    max_risk: int | None = None,
    last_seen_before=None,
    last_seen_after=None,
    q: str | None = None,
    exact: bool = False,
    sort: SortOrder = SortOrder.newest,
    page: int = 1,
    page_size: int = 50,
):
    alert_counts = (
        select(Alert.host_id, func.count().label("alert_count"))
        .where(Alert.status == "open")
        .group_by(Alert.host_id)
        .subquery()
    )
    query = (
        select(Host, HostThreatScore.score, alert_counts.c.alert_count)
        .outerjoin(HostThreatScore, Host.id == HostThreatScore.host_id)
        .outerjoin(alert_counts, Host.id == alert_counts.c.host_id)
    )
    count_q = select(func.count()).select_from(Host)
    clauses = []

    if hostname:
        clauses.append(
            or_(Host.name.ilike(f"%{hostname}%"), Host.hostname.ilike(f"%{hostname}%"))
            if not exact
            else or_(Host.name == hostname, Host.hostname == hostname)
        )
    if status:
        clauses.append(Host.status == status)
    if os_info:
        clauses.append(Host.os_info.ilike(f"%{os_info}%"))
    if min_risk is not None:
        clauses.append(HostThreatScore.score >= min_risk)
    if max_risk is not None:
        clauses.append(HostThreatScore.score <= max_risk)
    if last_seen_after:
        clauses.append(Host.last_seen >= last_seen_after)
    if last_seen_before:
        clauses.append(Host.last_seen <= last_seen_before)
    if q:
        pattern = q if exact else f"%{q}%"
        op = Host.name.__eq__ if exact else Host.name.ilike
        clauses.append(
            or_(
                op(pattern),
                Host.hostname.ilike(pattern) if not exact else Host.hostname == q,
                cast(Host.ip_address, String).ilike(pattern) if not exact else cast(Host.ip_address, String) == q,
            )
        )

    for c in clauses:
        query = query.where(c)
        count_q = count_q.where(c)

    total = (await db.execute(count_q)).scalar_one()

    if sort == SortOrder.risk_score:
        query = query.order_by(desc(HostThreatScore.score.nulls_last()))
    elif sort == SortOrder.host_name:
        query = query.order_by(Host.name.asc())
    elif sort == SortOrder.alert_count:
        query = query.order_by(desc(alert_counts.c.alert_count.nulls_last()))
    elif sort == SortOrder.oldest:
        query = query.order_by(Host.created_at.asc())
    else:
        query = query.order_by(Host.created_at.desc())

    rows = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    return rows.all(), total
