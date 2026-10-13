import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.brand import PRODUCT_NAME
from app.config import settings
from app.database import get_db
from app.dependencies import client_ip, get_current_user, require_roles
from app.models.alert import Alert
from app.models.enrollment import EnrollmentToken
from app.models.event import Event
from app.models.host import Host
from app.models.metric import Metric
from app.models.siem import HostRiskHistory
from app.models.threat_score import HostThreatScore
from app.models.user import User
from app.routers.auth import DEMO_USER_EMAIL
from app.schemas.host import AgentCertRegister, EnrollmentTokenResponse, HostCreate, HostListResponse, HostResponse
from app.schemas.host_risk import TokenListItem, RiskFactorItem, RiskHistoryItem, HostRiskResponse
from app.security import generate_enrollment_token, hash_token
from app.services.audit import log_audit
from app.services.export_service import respond_export
from app.services.query_builders import query_hosts
from app.utils.query import ListParams, SortOrder

router = APIRouter(prefix="/hosts", tags=["hosts"])

logger = logging.getLogger(__name__)

DEMO_HOST_NAME = "demo-server"


async def seed_demo_host(db: AsyncSession) -> None:
    """Seed one ready-to-use host so Attack Lab can run without manual setup."""
    if not settings.demo_mode or settings.testing:
        return
    if settings.environment == "production":
        return
    existing = (
        await db.execute(select(Host).where(Host.name == DEMO_HOST_NAME))
    ).scalar_one_or_none()
    if existing:
        return
    owner = (
        await db.execute(select(User).where(User.email == DEMO_USER_EMAIL))
    ).scalar_one_or_none() or (
        await db.execute(select(User).order_by(User.created_at).limit(1))
    ).scalar_one_or_none()
    if not owner:
        logger.warning("DEMO_MODE=true but no user exists yet — skipping demo host seed")
        return
    now = datetime.now(timezone.utc)
    db.add(
        Host(
            name=DEMO_HOST_NAME,
            hostname=DEMO_HOST_NAME,
            ip_address="127.0.0.1",
            os_info="Ubuntu 22.04 LTS",
            status="online",
            health_status="healthy",
            last_seen=now,
            created_by=owner.id,
        )
    )
    logger.info("DEMO_MODE=true — seeded demo host %s", DEMO_HOST_NAME)


def _host_row(host, score, alert_count) -> HostResponse:
    return HostResponse(
        id=host.id, name=host.name, hostname=host.hostname,
        ip_address=str(host.ip_address) if host.ip_address else None,
        os_info=host.os_info, status=host.status, enrolled=bool(host.api_key_hash),
        last_seen=host.last_seen,
        created_at=host.created_at, risk_score=score, alert_count=alert_count or 0,
    )


@router.post("", response_model=HostResponse)
async def create_host(body: HostCreate, request: Request, db: AsyncSession = Depends(get_db), user: User = Depends(require_roles("admin", "analyst"))):
    host = Host(name=body.name, created_by=user.id, status="inactive")
    db.add(host)
    await db.flush()
    await log_audit(db, "host_create", user_id=user.id, resource_type="host", resource_id=host.id, ip_address=client_ip(request))
    from app.search.indexer import index_host
    await index_host(host)
    return _host_row(host, None, 0)


@router.get("", response_model=HostListResponse)
async def list_hosts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    hostname: str | None = None,
    status: str | None = None,
    os_info: str | None = None,
    min_risk: int | None = None,
    max_risk: int | None = None,
    q: str | None = None,
    exact: bool = False,
    preset: str | None = ListParams.preset(),
    from_time: datetime | None = ListParams.from_time(),
    to_time: datetime | None = ListParams.to_time(),
    sort: SortOrder = ListParams.sort(),
    page: int = ListParams.page(),
    page_size: int = ListParams.page_size(),
):
    # Host inventory is not filtered by time range; preset/from/to are accepted but ignored.
    rows, total = await query_hosts(
        db, hostname=hostname, status=status, os_info=os_info,
        min_risk=min_risk, max_risk=max_risk,
        last_seen_after=None, last_seen_before=None,
        q=q, exact=exact, sort=sort, page=page, page_size=page_size,
    )
    items = [_host_row(h, score, ac) for h, score, ac in rows]
    return HostListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/export")
async def export_hosts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst")),
    format: str = Query("csv", pattern="^(csv|json|pdf)$"),
    hostname: str | None = None,
    status: str | None = None,
    sort: SortOrder = ListParams.sort(),
    page_size: int = Query(500, ge=1, le=500),
):
    rows, _ = await query_hosts(db, hostname=hostname, status=status, sort=sort, page=1, page_size=page_size)
    data = [{"name": h.name, "hostname": h.hostname, "status": h.status, "risk_score": score, "alerts": ac or 0} for h, score, ac in rows]
    from app.services.audit import log_audit
    await log_audit(db, "host_export", user_id=user.id, resource_type="host")
    return respond_export(data, format, filename_base="hosts", pdf_title=f"{PRODUCT_NAME} Hosts Export")


@router.get("/{host_id}", response_model=HostResponse)
async def get_host(host_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Host).where(Host.id == host_id))
    host = result.scalar_one_or_none()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    score_row = (
        await db.execute(select(HostThreatScore).where(HostThreatScore.host_id == host_id))
    ).scalar_one_or_none()
    alert_count = (
        await db.execute(
            select(func.count()).select_from(Alert).where(Alert.host_id == host_id, Alert.status == "open")
        )
    ).scalar_one()
    return _host_row(host, score_row.score if score_row else None, alert_count)


@router.get("/{host_id}/risk", response_model=HostRiskResponse)
async def get_host_risk(host_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    host = (await db.execute(select(Host).where(Host.id == host_id))).scalar_one_or_none()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    score_row = (
        await db.execute(select(HostThreatScore).where(HostThreatScore.host_id == host_id))
    ).scalar_one_or_none()
    factors = dict(score_row.factors or {}) if score_row else {}
    total = sum(factors.values()) or 1
    breakdown = [
        RiskFactorItem(name=k.replace("_", " ").title(), value=v, weight=round(v / total * 100, 1))
        for k, v in sorted(factors.items(), key=lambda x: -x[1])
    ]
    history_rows = (
        await db.execute(
            select(HostRiskHistory)
            .where(HostRiskHistory.host_id == host_id)
            .order_by(HostRiskHistory.recorded_at.desc())
            .limit(30)
        )
    ).scalars().all()
    history = [
        RiskHistoryItem(risk_score=h.risk_score, health_score=h.health_score, recorded_at=h.recorded_at)
        for h in reversed(history_rows)
    ]
    return HostRiskResponse(
        host_id=str(host.id),
        host_name=host.name,
        score=score_row.score if score_row else 0,
        health_score=score_row.health_score if score_row else 100,
        factors=factors,
        factor_breakdown=breakdown,
        history=history,
    )


@router.get("/{host_id}/flow-status")
async def get_host_flow_status(
    host_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Report whether the agent flow collector is delivering network_flow events."""
    host = (await db.execute(select(Host).where(Host.id == host_id))).scalar_one_or_none()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    row = (
        await db.execute(
            select(
                func.count().label("flow_count"),
                func.max(Event.timestamp).label("last_flow_at"),
            )
            .where(
                Event.host_id == host_id,
                Event.event_type == "network_flow",
                Event.timestamp >= since,
            )
        )
    ).one()
    distinct_ports = (
        await db.execute(
            select(func.count(func.distinct(Event.metadata_["dst_port"].astext)))
            .where(
                Event.host_id == host_id,
                Event.event_type == "network_flow",
                Event.timestamp >= since,
                Event.metadata_["dst_port"].is_not(None),
            )
        )
    ).scalar_one()
    last_flow_at = row.last_flow_at
    collector_active = bool(
        last_flow_at
        and (datetime.now(timezone.utc) - (last_flow_at if last_flow_at.tzinfo else last_flow_at.replace(tzinfo=timezone.utc))).total_seconds() < 300
    )
    return {
        "host_id": str(host.id),
        "collector_active": collector_active,
        "flow_count_24h": row.flow_count or 0,
        "distinct_dst_ports_24h": distinct_ports or 0,
        "last_flow_at": last_flow_at.isoformat() if last_flow_at else None,
    }


HEARTBEAT_RECENT_SECONDS = 90  # agent heartbeat interval is 30s; 3x = stale


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@router.get("/{host_id}/agent-status")
async def get_host_agent_status(
    host_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Operational agent status from real backend data only.

    Distinguishes confirmed absence (e.g. enrolled but no heartbeats ever)
    from missing telemetry (e.g. agent never reported delivery stats).
    A host record alone never implies a healthy agent.
    """
    host = (await db.execute(select(Host).where(Host.id == host_id))).scalar_one_or_none()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    now = datetime.now(timezone.utc)
    last_seen = _as_utc(host.last_seen)
    if last_seen is None:
        heartbeat_state = "never"
        heartbeat_age_seconds = None
    else:
        heartbeat_age_seconds = max(0.0, (now - last_seen).total_seconds())
        heartbeat_state = "recent" if heartbeat_age_seconds <= HEARTBEAT_RECENT_SECONDS else "stale"

    last_event_at = _as_utc(
        (await db.execute(
            select(func.max(Event.timestamp)).where(Event.host_id == host_id)
        )).scalar_one_or_none()
    )
    last_metric_at = _as_utc(
        (await db.execute(
            select(func.max(Metric.recorded_at)).where(Metric.host_id == host_id)
        )).scalar_one_or_none()
    )

    since = now - timedelta(hours=24)
    flow_row = (
        await db.execute(
            select(
                func.count().label("flow_count"),
                func.max(Event.timestamp).label("last_flow_at"),
            ).where(
                Event.host_id == host_id,
                Event.event_type == "network_flow",
                Event.timestamp >= since,
            )
        )
    ).one()
    last_flow_at = _as_utc(flow_row.last_flow_at)
    flow_collector_active = bool(
        last_flow_at and (now - last_flow_at).total_seconds() < 300
    )

    delivery_stats = dict(host.delivery_stats) if host.delivery_stats else None
    pending_tokens = (
        await db.execute(
            select(func.count())
            .select_from(EnrollmentToken)
            .where(
                EnrollmentToken.host_id == host_id,
                EnrollmentToken.used_at.is_(None),
                EnrollmentToken.revoked_at.is_(None),
                EnrollmentToken.expires_at > now,
            )
        )
    ).scalar_one()

    messages: list[str] = []
    if not host.api_key_hash:
        messages.append("Host has never enrolled — no agent credentials exist.")
    elif host.api_key_revoked_at:
        messages.append("Agent credentials were revoked; the agent must re-enroll.")
    if heartbeat_state == "never" and host.api_key_hash:
        messages.append("Enrolled, but no heartbeat has ever been received — the agent is not running or cannot reach the API.")
    elif heartbeat_state == "stale":
        messages.append(f"No heartbeat for {int(heartbeat_age_seconds or 0)}s — the agent may be down or disconnected.")
    if last_event_at is None and heartbeat_state == "recent":
        messages.append("Agent is heartbeating but has delivered no events — telemetry collection may be disabled or the host is idle.")
    if delivery_stats is None and heartbeat_state == "recent":
        messages.append("Agent has not reported delivery statistics (older agent version or first heartbeat pending).")

    return {
        "host_id": str(host.id),
        "name": host.name,
        "hostname": host.hostname,
        "ip_address": str(host.ip_address) if host.ip_address else None,
        "os_info": host.os_info,
        "status": host.status,
        "enrolled": bool(host.api_key_hash) and host.api_key_revoked_at is None,
        "api_key_created_at": host.api_key_created_at.isoformat() if host.api_key_created_at else None,
        "api_key_revoked_at": host.api_key_revoked_at.isoformat() if host.api_key_revoked_at else None,
        "pending_enrollment_tokens": pending_tokens or 0,
        "agent_version": host.agent_version,
        "integrity_recorded": bool(host.agent_hash),
        "agent_hash_changed_at": host.agent_hash_changed_at.isoformat() if host.agent_hash_changed_at else None,
        "last_seen": last_seen.isoformat() if last_seen else None,
        "heartbeat_state": heartbeat_state,
        "heartbeat_age_seconds": heartbeat_age_seconds,
        "last_event_at": last_event_at.isoformat() if last_event_at else None,
        "last_metric_at": last_metric_at.isoformat() if last_metric_at else None,
        "flow_collector_active": flow_collector_active,
        "flow_count_24h": flow_row.flow_count or 0,
        "last_flow_at": last_flow_at.isoformat() if last_flow_at else None,
        "delivery_stats": delivery_stats,
        "delivery_stats_source": "agent_heartbeat" if delivery_stats else None,
        "checked_at": now.isoformat(),
        "messages": messages,
    }


@router.delete("/{host_id}")
async def delete_host(host_id: UUID, request: Request, db: AsyncSession = Depends(get_db), user: User = Depends(require_roles("admin"))):
    result = await db.execute(select(Host).where(Host.id == host_id))
    host = result.scalar_one_or_none()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    from sqlalchemy import text
    from app.database import async_session

    hid = str(host_id)
    stmts = [
        "DELETE FROM offense_events WHERE offense_id IN (SELECT id FROM offenses WHERE host_id = CAST(:hid AS UUID))",
        "DELETE FROM offense_events WHERE event_id IN (SELECT id FROM events WHERE host_id = CAST(:hid AS UUID))",
        "DELETE FROM offense_events WHERE alert_id IN (SELECT id FROM alerts WHERE host_id = CAST(:hid AS UUID))",
        "DELETE FROM correlation_results WHERE host_id = CAST(:hid AS UUID)",
        "DELETE FROM attack_timelines WHERE host_id = CAST(:hid AS UUID)",
        "DELETE FROM host_risk_scores WHERE host_id = CAST(:hid AS UUID)",
        "DELETE FROM host_threat_scores WHERE host_id = CAST(:hid AS UUID)",
        "DELETE FROM alerts WHERE host_id = CAST(:hid AS UUID)",
        "DELETE FROM events WHERE host_id = CAST(:hid AS UUID)",
        "DELETE FROM metrics WHERE host_id = CAST(:hid AS UUID)",
        "DELETE FROM offenses WHERE host_id = CAST(:hid AS UUID)",
        "DELETE FROM enrollment_tokens WHERE host_id = CAST(:hid AS UUID)",
        "DELETE FROM agent_request_nonces WHERE host_id = CAST(:hid AS UUID)",
        "DELETE FROM maintenance_windows WHERE host_id = CAST(:hid AS UUID)",
        "DELETE FROM simulation_runs WHERE host_id = CAST(:hid AS UUID)",
        "UPDATE incidents SET host_id = NULL WHERE host_id = CAST(:hid AS UUID)",
        "DELETE FROM hosts WHERE id = CAST(:hid AS UUID)",
    ]
    for stmt in stmts:
        try:
            async with async_session() as s:
                await s.execute(text(stmt), {"hid": hid})
                await s.commit()
        except Exception:
            pass
    await log_audit(db, "host_delete", user_id=user.id, resource_type="host", resource_id=host_id, ip_address=client_ip(request))
    return {"message": "Host deleted"}


@router.post("/{host_id}/enrollment-token", response_model=EnrollmentTokenResponse)
async def create_enrollment_token(host_id: UUID, request: Request, db: AsyncSession = Depends(get_db), user: User = Depends(require_roles("admin", "analyst"))):
    result = await db.execute(select(Host).where(Host.id == host_id))
    host = result.scalar_one_or_none()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    token = generate_enrollment_token()
    expires = datetime.now(timezone.utc) + timedelta(hours=24)
    db.add(EnrollmentToken(host_id=host.id, token_hash=hash_token(token), expires_at=expires, created_by=user.id))
    install_command = (
        f"curl -fsSL {settings.server_url}/install.sh | sudo bash -s -- "
        f"--token {token} --server {settings.server_url}"
    )
    await log_audit(db, "enrollment_token_create", user_id=user.id, resource_type="host", resource_id=host_id, ip_address=client_ip(request))
    mtls_note = None
    if settings.agent_mtls_enabled:
        mtls_note = f"Generate client cert, then POST fingerprint to /api/v1/hosts/{host_id}/agent-cert"
    return EnrollmentTokenResponse(
        token=token, expires_at=expires, install_command=install_command,
        host_id=host.id, host_name=host.name, mtls_note=mtls_note,
    )


@router.post("/{host_id}/agent-cert")
async def register_agent_cert(
    host_id: UUID,
    body: AgentCertRegister,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst")),
):
    """Register agent TLS certificate fingerprint for mTLS verification."""
    host = (await db.execute(select(Host).where(Host.id == host_id))).scalar_one_or_none()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    host.agent_cert_fingerprint = body.cert_fingerprint.lower()
    await log_audit(
        db,
        "agent_cert_register",
        user_id=user.id,
        resource_type="host",
        resource_id=host_id,
        ip_address=client_ip(request),
    )
    return {"host_id": str(host_id), "agent_cert_fingerprint": host.agent_cert_fingerprint, "ok": True}


@router.get("/{host_id}/enrollment-tokens", response_model=list[TokenListItem])
async def list_enrollment_tokens(host_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(require_roles("admin", "analyst"))):
    result = await db.execute(select(EnrollmentToken).where(EnrollmentToken.host_id == host_id).order_by(EnrollmentToken.created_at.desc()))
    return list(result.scalars().all())


@router.delete("/enrollment-tokens/{token_id}")
async def revoke_token(token_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(require_roles("admin", "analyst"))):
    result = await db.execute(select(EnrollmentToken).where(EnrollmentToken.id == token_id, EnrollmentToken.used_at.is_(None)))
    token = result.scalar_one_or_none()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found or already used")
    token.revoked_at = datetime.now(timezone.utc)
    token.revoked_by = user.id
    await log_audit(db, "enrollment_token_revoke", user_id=user.id, resource_id=token_id)
    return {"message": "Token revoked"}
