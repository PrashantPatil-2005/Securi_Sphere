"""UEBA baseline anomaly detection — z-score spikes vs rolling daily baselines."""

from __future__ import annotations

import logging
import statistics
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.analytics import AnalyticsDailyStat
from app.models.event import Event
from app.models.host import Host
from app.models.ueba import UebaAnomaly

logger = logging.getLogger(__name__)

AUTH_EVENT_TYPES = frozenset({
    "ssh_login_failure",
    "ssh_login_success",
    "sudo_usage",
    "root_login",
})

METRIC_STAT_NAMES = {
    "failed_logins": "ueba_failed_logins",
    "auth_events": "ueba_auth_events",
    "events_total": "ueba_events_total",
}


def compute_z_score(observed: float, mean: float, stddev: float) -> float:
    spread = max(stddev, 1.0)
    return (observed - mean) / spread


def severity_from_z(z: float) -> str:
    if z >= 5:
        return "critical"
    if z >= 4:
        return "high"
    if z >= 3:
        return "medium"
    return "low"


async def get_baseline_stats(
    db: AsyncSession,
    metric_name: str,
    dimension_key: str,
    *,
    days: int | None = None,
) -> tuple[float, float, int] | None:
    window = days or settings.ueba_baseline_days
    since = datetime.now(timezone.utc).date() - timedelta(days=window)
    rows = (
        await db.execute(
            select(AnalyticsDailyStat.value)
            .where(
                AnalyticsDailyStat.metric_name == metric_name,
                AnalyticsDailyStat.dimension_key == dimension_key,
                AnalyticsDailyStat.stat_date >= since,
                AnalyticsDailyStat.stat_date < datetime.now(timezone.utc).date(),
            )
            .order_by(AnalyticsDailyStat.stat_date)
        )
    ).scalars().all()
    if len(rows) < settings.ueba_min_baseline_samples:
        return None
    mean = statistics.mean(rows)
    stddev = statistics.pstdev(rows) if len(rows) > 1 else max(mean * 0.25, 1.0)
    return mean, stddev, len(rows)


async def _count_host_events(
    db: AsyncSession,
    host_id,
    *,
    hours: int,
    event_types: set[str] | None = None,
) -> int:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    clauses = [Event.host_id == host_id, Event.timestamp >= since]
    if event_types:
        clauses.append(Event.event_type.in_(event_types))
    return (
        await db.execute(select(func.count()).select_from(Event).where(*clauses))
    ).scalar_one()


async def _count_user_events(
    db: AsyncSession,
    username: str,
    *,
    hours: int,
    event_types: set[str] | None = None,
) -> int:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    clauses = [Event.username == username, Event.timestamp >= since]
    if event_types:
        clauses.append(Event.event_type.in_(event_types))
    return (
        await db.execute(select(func.count()).select_from(Event).where(*clauses))
    ).scalar_one()


async def _existing_open(
    db: AsyncSession,
    entity_type: str,
    entity_key: str,
    metric: str,
) -> UebaAnomaly | None:
    return (
        await db.execute(
            select(UebaAnomaly).where(
                UebaAnomaly.entity_type == entity_type,
                UebaAnomaly.entity_key == entity_key,
                UebaAnomaly.metric == metric,
                UebaAnomaly.status == "open",
            )
        )
    ).scalar_one_or_none()


async def _record_anomaly(
    db: AsyncSession,
    *,
    entity_type: str,
    entity_key: str,
    entity_label: str,
    metric: str,
    observed: int,
    mean: float,
    stddev: float,
    z: float,
    context: dict,
) -> UebaAnomaly | None:
    if observed < settings.ueba_min_observed:
        return None
    if z < settings.ueba_z_threshold:
        return None

    existing = await _existing_open(db, entity_type, entity_key, metric)
    if existing:
        existing.observed_value = observed
        existing.baseline_mean = mean
        existing.baseline_stddev = stddev
        existing.z_score = z
        existing.severity = severity_from_z(z)
        existing.context = {**existing.context, **context, "updated": True}
        existing.description = (
            f"{entity_label}: {metric.replace('_', ' ')} spike — "
            f"{observed} in {settings.ueba_window_hours}h vs baseline μ={mean:.1f} (z={z:.1f})"
        )
        await db.flush()
        return existing

    severity = severity_from_z(z)
    anomaly = UebaAnomaly(
        entity_type=entity_type,
        entity_key=entity_key,
        entity_label=entity_label,
        metric=metric,
        observed_value=observed,
        baseline_mean=mean,
        baseline_stddev=stddev,
        z_score=z,
        severity=severity,
        status="open",
        description=(
            f"{entity_label}: {metric.replace('_', ' ')} spike — "
            f"{observed} in {settings.ueba_window_hours}h vs baseline μ={mean:.1f} (z={z:.1f})"
        ),
        context=context,
    )
    db.add(anomaly)
    await db.flush()

    if settings.ueba_create_alerts and severity in ("high", "critical"):
        await _maybe_create_alert(db, anomaly)

    return anomaly


async def _maybe_create_alert(db: AsyncSession, anomaly: UebaAnomaly) -> None:
    if anomaly.entity_type != "host":
        return
    from uuid import UUID

    from app.services.detection import create_alert

    host = await db.get(Host, UUID(anomaly.entity_key))
    if not host:
        return

    alert = await create_alert(
        db,
        host.id,
        f"UEBA: {anomaly.metric.replace('_', ' ').title()}",
        anomaly.description,
        anomaly.severity,
    )
    if alert:
        anomaly.alert_id = alert.id
        await db.flush()


async def _evaluate_entity(
    db: AsyncSession,
    *,
    entity_type: str,
    entity_key: str,
    entity_label: str,
    metric: str,
    observed: int,
) -> UebaAnomaly | None:
    stat_name = METRIC_STAT_NAMES[metric]
    baseline = await get_baseline_stats(db, stat_name, entity_key)
    if not baseline:
        return None
    mean, stddev, samples = baseline
    window_fraction = settings.ueba_window_hours / 24.0
    expected = max(mean * window_fraction, 0.5)
    adjusted_stddev = max(stddev * window_fraction, 1.0)
    z = compute_z_score(float(observed), expected, adjusted_stddev)
    return await _record_anomaly(
        db,
        entity_type=entity_type,
        entity_key=entity_key,
        entity_label=entity_label,
        metric=metric,
        observed=observed,
        mean=expected,
        stddev=adjusted_stddev,
        z=z,
        context={"baseline_samples": samples, "window_hours": settings.ueba_window_hours},
    )


async def scan_ueba_anomalies(db: AsyncSession) -> dict:
    """Scan hosts and users for baseline deviations. Returns summary counts."""
    if not settings.ueba_enabled:
        return {"enabled": False, "created": 0, "updated": 0}

    created = 0
    updated = 0
    hours = settings.ueba_window_hours

    hosts = list((await db.execute(select(Host).where(Host.api_key_hash.isnot(None)))).scalars().all())
    for host in hosts:
        for metric, counter in (
            ("failed_logins", lambda h: _count_host_events(db, h.id, hours=hours, event_types={"ssh_login_failure"})),
            ("auth_events", lambda h: _count_host_events(db, h.id, hours=hours, event_types=AUTH_EVENT_TYPES)),
            ("events_total", lambda h: _count_host_events(db, h.id, hours=hours)),
        ):
            observed = await counter(host)
            before = await _existing_open(db, "host", str(host.id), metric)
            result = await _evaluate_entity(
                db,
                entity_type="host",
                entity_key=str(host.id),
                entity_label=host.name or host.hostname or str(host.id)[:8],
                metric=metric,
                observed=observed,
            )
            if result:
                if before:
                    updated += 1
                else:
                    created += 1

    usernames = (
        await db.execute(
            select(Event.username)
            .where(
                Event.username.isnot(None),
                Event.timestamp >= datetime.now(timezone.utc) - timedelta(days=settings.ueba_baseline_days + 1),
            )
            .distinct()
            .limit(500)
        )
    ).scalars().all()

    for username in usernames:
        if not username:
            continue
        for metric, counter in (
            ("failed_logins", lambda u: _count_user_events(db, u, hours=hours, event_types={"ssh_login_failure"})),
            ("auth_events", lambda u: _count_user_events(db, u, hours=hours, event_types=AUTH_EVENT_TYPES)),
        ):
            observed = await counter(username)
            before = await _existing_open(db, "user", username, metric)
            result = await _evaluate_entity(
                db,
                entity_type="user",
                entity_key=username,
                entity_label=username,
                metric=metric,
                observed=observed,
            )
            if result:
                if before:
                    updated += 1
                else:
                    created += 1

    logger.info("ueba scan complete", extra={"created": created, "updated": updated})
    return {"enabled": True, "created": created, "updated": updated, "hosts_scanned": len(hosts), "users_scanned": len(usernames)}
