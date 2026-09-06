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
from app.models.host import Host
from app.models.siem import HostRiskHistory
from app.models.threat_score import HostThreatScore
from app.models.user import User
from app.schemas.host import AgentCertRegister, EnrollmentTokenResponse, HostCreate, HostListResponse, HostResponse
from app.schemas.host_risk import TokenListItem, RiskFactorItem, RiskHistoryItem, HostRiskResponse
from app.security import generate_enrollment_token, hash_token
from app.services.audit import log_audit
from app.services.export_service import respond_export
from app.services.query_builders import query_hosts
from app.utils.query import ListParams, SortOrder

router = APIRouter(prefix="/hosts", tags=["hosts"])


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
