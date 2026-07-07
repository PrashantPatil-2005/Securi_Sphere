"""Admin user management and invite flow."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import require_roles
from app.models.role import Role
from app.models.user import User
from app.models.user_invite import UserInvite
from app.schemas.users import (
    InviteAcceptRequest,
    InvitePreviewResponse,
    UserAdminResponse,
    UserInviteCreateRequest,
    UserInviteResponse,
    UserProvisionRequest,
    UserUpdateRequest,
)
from app.services.audit import log_audit
from app.services.user_provisioning import (
    accept_invite,
    create_invite,
    get_invite_preview,
    provision_user,
    send_invite_email,
    user_admin_dict,
)

router = APIRouter(prefix="/users", tags=["users"])


def _invite_response(invite: UserInvite, role_name: str, invite_url: str | None = None) -> UserInviteResponse:
    return UserInviteResponse(
        id=invite.id,
        email=invite.email,
        full_name=invite.full_name,
        role=role_name,
        expires_at=invite.expires_at,
        accepted_at=invite.accepted_at,
        created_at=invite.created_at,
        invite_url=invite_url,
    )


@router.get("", response_model=list[UserAdminResponse])
async def list_users(db: AsyncSession = Depends(get_db), user: User = Depends(require_roles("admin"))):
    rows = list(
        (await db.execute(select(User).options(selectinload(User.role)).order_by(User.created_at.desc()))).scalars().all()
    )
    return [user_admin_dict(u) for u in rows]


@router.post("", response_model=UserAdminResponse, status_code=201)
async def create_user(
    body: UserProvisionRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
):
    created = await provision_user(
        db,
        email=body.email,
        role_name=body.role,
        full_name=body.full_name,
        password=body.password,
        sso_only=body.sso_only,
    )
    await log_audit(db, "user_provisioned", user_id=admin.id, details={"email": body.email, "role": body.role})
    return user_admin_dict(created)


@router.patch("/{user_id}", response_model=UserAdminResponse)
async def update_user(
    user_id: UUID,
    body: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
):
    target = (
        await db.execute(select(User).options(selectinload(User.role)).where(User.id == user_id))
    ).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == admin.id and body.is_active is False:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    if body.role is not None:
        role = (await db.execute(select(Role).where(Role.name == body.role))).scalar_one_or_none()
        if not role:
            raise HTTPException(status_code=400, detail="Unknown role")
        if target.id == admin.id and body.role != "admin":
            raise HTTPException(status_code=400, detail="Cannot change your own admin role")
        target.role_id = role.id
    if body.is_active is not None:
        target.is_active = body.is_active

    await db.flush()
    result = await db.execute(select(User).options(selectinload(User.role)).where(User.id == user_id))
    await log_audit(db, "user_updated", user_id=admin.id, details={"target_id": str(user_id)})
    return user_admin_dict(result.scalar_one())


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
):
    target = (
        await db.execute(select(User).options(selectinload(User.role)).where(User.id == user_id))
    ).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    if target.role.name == "admin":
        admin_role = (await db.execute(select(Role).where(Role.name == "admin"))).scalar_one()
        active_admins = (
            await db.execute(
                select(func.count())
                .select_from(User)
                .where(User.role_id == admin_role.id, User.is_active.is_(True), User.id != target.id)
            )
        ).scalar_one()
        if active_admins < 1:
            raise HTTPException(status_code=400, detail="Cannot delete the last active admin")

    email = target.email
    target.is_active = False
    target.email = f"deleted-{target.id}@removed.local"
    target.hashed_password = ""
    target.oidc_sub = None
    await db.flush()
    await log_audit(db, "user_deleted", user_id=admin.id, details={"email": email, "target_id": str(user_id)})


@router.get("/invites", response_model=list[UserInviteResponse])
async def list_invites(db: AsyncSession = Depends(get_db), user: User = Depends(require_roles("admin"))):
    invites = list(
        (
            await db.execute(
                select(UserInvite, Role.name)
                .join(Role, Role.id == UserInvite.role_id)
                .where(UserInvite.accepted_at.is_(None))
                .order_by(UserInvite.created_at.desc())
            )
        ).all()
    )
    return [_invite_response(inv, role_name) for inv, role_name in invites]


@router.post("/invites", response_model=UserInviteResponse, status_code=201)
async def invite_user(
    body: UserInviteCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
):
    invite, raw_token = await create_invite(
        db,
        email=body.email,
        role_name=body.role,
        full_name=body.full_name,
        invited_by=admin,
    )
    invite_url = await send_invite_email(body.email, raw_token)
    await log_audit(db, "user_invited", user_id=admin.id, details={"email": body.email, "role": body.role})
    role = (await db.execute(select(Role).where(Role.id == invite.role_id))).scalar_one()
    return _invite_response(invite, role.name, invite_url)


@router.delete("/invites/{invite_id}", status_code=204)
async def revoke_invite(
    invite_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
):
    invite = (await db.execute(select(UserInvite).where(UserInvite.id == invite_id))).scalar_one_or_none()
    if not invite or invite.accepted_at:
        raise HTTPException(status_code=404, detail="Invite not found")
    await db.delete(invite)
    await log_audit(db, "user_invite_revoked", user_id=admin.id, details={"email": invite.email})


@router.get("/invites/preview", response_model=InvitePreviewResponse)
async def preview_invite(token: str, db: AsyncSession = Depends(get_db)):
    invite = await get_invite_preview(db, token)
    role = (await db.execute(select(Role).where(Role.id == invite.role_id))).scalar_one()
    return InvitePreviewResponse(
        email=invite.email,
        full_name=invite.full_name,
        role=role.name,
        expires_at=invite.expires_at,
    )


@router.post("/invites/accept", response_model=UserAdminResponse)
async def accept_user_invite(body: InviteAcceptRequest, db: AsyncSession = Depends(get_db)):
    if not body.password:
        from app.services.oidc import oidc_configured

        if not oidc_configured():
            raise HTTPException(status_code=400, detail="Password required (SSO not configured)")
    user = await accept_invite(
        db,
        raw_token=body.token,
        password=body.password,
        full_name=body.full_name,
    )
    await log_audit(db, "user_invite_accepted", user_id=user.id, details={"email": user.email})
    return user_admin_dict(user)
