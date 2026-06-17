from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import client_ip, get_current_user, require_roles
from app.models.enrollment import EnrollmentToken
from app.models.host import Host
from app.models.user import User
from app.schemas.host import EnrollmentTokenResponse, HostCreate, HostResponse
from app.security import generate_enrollment_token, hash_token
from app.services.audit import log_audit

router = APIRouter(prefix="/hosts", tags=["hosts"])


@router.post("", response_model=HostResponse)
async def create_host(
    body: HostCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst")),
):
    host = Host(name=body.name, created_by=user.id, status="offline")
    db.add(host)
    await db.flush()
    await log_audit(db, "host_create", user_id=user.id, resource_type="host", resource_id=host.id, ip_address=client_ip(request))
    return host


@router.get("", response_model=list[HostResponse])
async def list_hosts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Host).order_by(Host.created_at.desc()))
    return list(result.scalars().all())


@router.get("/{host_id}", response_model=HostResponse)
async def get_host(
    host_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Host).where(Host.id == host_id))
    host = result.scalar_one_or_none()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    return host


@router.delete("/{host_id}")
async def delete_host(
    host_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    result = await db.execute(select(Host).where(Host.id == host_id))
    host = result.scalar_one_or_none()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    await db.delete(host)
    await log_audit(db, "host_delete", user_id=user.id, resource_type="host", resource_id=host_id, ip_address=client_ip(request))
    return {"message": "Host deleted"}


@router.post("/{host_id}/enrollment-token", response_model=EnrollmentTokenResponse)
async def create_enrollment_token(
    host_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst")),
):
    result = await db.execute(select(Host).where(Host.id == host_id))
    host = result.scalar_one_or_none()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    token = generate_enrollment_token()
    expires = datetime.now(timezone.utc) + timedelta(hours=24)
    db.add(EnrollmentToken(
        host_id=host.id,
        token_hash=hash_token(token),
        expires_at=expires,
        created_by=user.id,
    ))
    install_command = (
        f"curl -s {settings.server_url}/install.sh | sudo bash -s -- "
        f"--token {token} --server {settings.server_url}"
    )
    await log_audit(db, "enrollment_token_create", user_id=user.id, resource_type="host", resource_id=host_id, ip_address=client_ip(request))
    return EnrollmentTokenResponse(token=token, expires_at=expires, install_command=install_command)
