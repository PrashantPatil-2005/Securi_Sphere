import logging

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.brand import PRODUCT_NAME
from app.config import settings
from app.database import get_db
from app.dependencies import client_ip, require_roles
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.validators import InetStr
from app.services.audit import log_audit
from app.services.audit_chain import verify_audit_chain
from app.services.export_service import respond_export

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditResponse(BaseModel):
    id: UUID
    user_id: UUID | None
    action: str
    resource_type: str | None
    resource_id: UUID | None
    ip_address: InetStr
    details: dict | None
    timestamp: datetime
    model_config = {"from_attributes": True}


class AuditIntegrityFailure(BaseModel):
    chain_seq: int
    reason: str
    expected: str | None = None
    actual: str | None = None


class AuditIntegrityResponse(BaseModel):
    valid: bool
    immutable_enabled: bool
    entries_checked: int
    chain_head_hash: str | None
    latest_chain_seq: int | None
    #: False when the verified window stopped before the newest audit entry
    #: (limit/from_seq window) — the tail of the chain was NOT checked.
    window_complete: bool = True
    failure: AuditIntegrityFailure | None = None


def _audit_query(
    *,
    action: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
) -> Select[tuple[AuditLog]]:
    q = select(AuditLog).order_by(AuditLog.timestamp.desc())
    if action:
        q = q.where(AuditLog.action == action)
    if from_time:
        q = q.where(AuditLog.timestamp >= from_time)
    if to_time:
        q = q.where(AuditLog.timestamp <= to_time)
    return q


def _audit_rows(logs: list[AuditLog]) -> list[dict]:
    return [
        {
            "id": str(log.id),
            "user_id": str(log.user_id) if log.user_id else "",
            "action": log.action,
            "resource_type": log.resource_type or "",
            "resource_id": str(log.resource_id) if log.resource_id else "",
            "ip_address": str(log.ip_address) if log.ip_address else "",
            "details": log.details,
            "timestamp": log.timestamp.isoformat(),
        }
        for log in logs
    ]


@router.get("", response_model=list[AuditResponse])
async def list_audit_logs(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin")),
    action: str | None = None,
    from_time: datetime | None = Query(None, alias="from"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    q = _audit_query(action=action, from_time=from_time)
    q = q.offset((page - 1) * page_size).limit(page_size)
    return list((await db.execute(q)).scalars().all())


@router.get("/export")
async def export_audit_logs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin")),
    format: str = Query("csv", pattern="^(csv|json|pdf)$"),
    action: str | None = None,
    from_time: datetime | None = Query(None, alias="from"),
    to_time: datetime | None = Query(None, alias="to"),
    limit: int = Query(5000, ge=1, le=10000),
):
    q = _audit_query(action=action, from_time=from_time, to_time=to_time).limit(limit)
    logs = list((await db.execute(q)).scalars().all())
    rows = _audit_rows(logs)

    await log_audit(
        db,
        "audit_export",
        user_id=user.id,
        ip_address=client_ip(request),
        details={
            "format": format,
            "row_count": len(rows),
            "action_filter": action,
            "from": from_time.isoformat() if from_time else None,
            "to": to_time.isoformat() if to_time else None,
        },
    )
    await db.commit()

    return respond_export(rows, format, filename_base="audit_logs", pdf_title=f"{PRODUCT_NAME} Audit Log Export")


@router.get("/integrity", response_model=AuditIntegrityResponse)
async def verify_audit_integrity(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin")),
    limit: int | None = Query(None, ge=1, le=1_000_000),
    from_seq: int | None = Query(None, ge=1),
):
    """Verify the audit hash chain.

    By default the FULL chain is verified (no limit). Pass an explicit
    `limit`/`from_seq` to check a window of a very large chain — the response
    then reports `window_complete=false` if the tail was not covered.

    On failure the endpoint still returns HTTP 200 (integrity state is data,
    not a transport error) but:
    - writes an `audit_integrity_failure` audit entry (best-effort) so the
      tamper attempt is itself recorded in the (possibly broken) chain,
    - logs an ERROR for server-side monitoring,
    - returns honest `entries_checked` (how many entries verified before the
      first mismatch) and the failure details.
    """
    # Default (no limit, no from_seq): verify the entire chain so a long
    # history cannot silently leave its tail unchecked.
    effective_limit = limit
    if from_seq is None and limit is None:
        effective_limit = None

    result = await verify_audit_chain(db, limit=effective_limit, from_seq=from_seq)
    failure = None
    if result.failure:
        failure = AuditIntegrityFailure(
            chain_seq=result.failure.chain_seq,
            reason=result.failure.reason,
            expected=result.failure.expected,
            actual=result.failure.actual,
        )
        # Record the failure itself so tampering is not silent. Best-effort:
        # if this write fails (e.g. the break is severe), the response still
        # carries the failure details.
        logger.error(
            "Audit chain integrity failure at chain_seq=%s reason=%s "
            "(entries_checked=%s, window_complete=%s)",
            result.failure.chain_seq,
            result.failure.reason,
            result.entries_checked,
            result.window_complete,
        )
        try:
            await log_audit(
                db,
                user_id=user.id,
                action="audit_integrity_failure",
                resource_type="audit_chain",
                resource_id=None,
                ip_address=client_ip(request),
                details={
                    "chain_seq": result.failure.chain_seq,
                    "reason": result.failure.reason,
                    "entries_checked": result.entries_checked,
                    "window_complete": result.window_complete,
                },
            )
            await db.commit()
        except Exception:
            logger.exception("failed to record audit_integrity_failure entry")
            await db.rollback()
    return AuditIntegrityResponse(
        valid=result.valid,
        immutable_enabled=settings.audit_immutable,
        entries_checked=result.entries_checked,
        chain_head_hash=result.chain_head_hash,
        latest_chain_seq=result.latest_chain_seq,
        window_complete=result.window_complete,
        failure=failure,
    )
