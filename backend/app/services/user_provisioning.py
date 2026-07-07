"""Admin user provisioning and invite acceptance."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.brand import PRODUCT_NAME
from app.config import settings
from app.models.role import Role
from app.models.user import User
from app.models.user_invite import UserInvite
from app.schemas.auth import RoleResponse
from app.security import generate_reset_token, hash_password, hash_token
from app.services.notifications import send_email


INVITE_TTL_DAYS = 7


def user_admin_response(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": RoleResponse.model_validate(user.role),
        "is_active": user.is_active,
        "last_login": user.last_login,
        "sso_only": user.hashed_password is None,
        "oidc_linked": bool(user.oidc_sub),
    }


def user_admin_dict(user: User) -> dict:
    return user_admin_response(user)


async def _role_by_name(db: AsyncSession, name: str) -> Role:
    role = (await db.execute(select(Role).where(Role.name == name))).scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=400, detail=f"Unknown role: {name}")
    return role


async def provision_user(
    db: AsyncSession,
    *,
    email: str,
    role_name: str,
    full_name: str | None,
    password: str | None,
    sso_only: bool,
) -> User:
    email = email.strip().lower()
    existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    if sso_only and password:
        raise HTTPException(status_code=400, detail="SSO-only users cannot have a password set here")

    if not sso_only and not password:
        raise HTTPException(status_code=400, detail="Password required unless sso_only is true")

    role = await _role_by_name(db, role_name)
    user = User(
        email=email,
        full_name=full_name,
        hashed_password=hash_password(password) if password else None,
        role_id=role.id,
    )
    db.add(user)
    await db.flush()
    result = await db.execute(select(User).options(selectinload(User.role)).where(User.id == user.id))
    return result.scalar_one()


async def create_invite(
    db: AsyncSession,
    *,
    email: str,
    role_name: str,
    full_name: str | None,
    invited_by: User,
) -> tuple[UserInvite, str]:
    email = email.strip().lower()
    existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    pending = (
        await db.execute(
            select(UserInvite).where(
                UserInvite.email == email,
                UserInvite.accepted_at.is_(None),
                UserInvite.expires_at > datetime.now(timezone.utc),
            )
        )
    ).scalar_one_or_none()
    if pending:
        raise HTTPException(status_code=400, detail="Pending invite already exists for this email")

    role = await _role_by_name(db, role_name)
    raw_token = generate_reset_token()
    invite = UserInvite(
        email=email,
        full_name=full_name,
        role_id=role.id,
        token_hash=hash_token(raw_token),
        invited_by_id=invited_by.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=INVITE_TTL_DAYS),
    )
    db.add(invite)
    await db.flush()
    return invite, raw_token


async def send_invite_email(email: str, raw_token: str) -> str:
    invite_url = f"{settings.frontend_url.rstrip('/')}/accept-invite?token={raw_token}"
    await send_email(
        email,
        f"You're invited to {PRODUCT_NAME}",
        f"<p>You have been invited to join {PRODUCT_NAME}.</p>"
        f"<p><a href='{invite_url}'>Accept invitation</a></p>"
        f"<p>Or open: {invite_url}</p>",
    )
    return invite_url


async def get_invite_preview(db: AsyncSession, raw_token: str) -> UserInvite:
    token_hash = hash_token(raw_token)
    invite = (
        await db.execute(select(UserInvite).where(UserInvite.token_hash == token_hash))
    ).scalar_one_or_none()
    if not invite or invite.accepted_at or invite.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired invite")
    return invite


async def accept_invite(
    db: AsyncSession,
    *,
    raw_token: str,
    password: str | None,
    full_name: str | None,
) -> User:
    invite = await get_invite_preview(db, raw_token)

    existing = (await db.execute(select(User).where(User.email == invite.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    if password:
        hashed = hash_password(password)
    else:
        hashed = None

    user = User(
        email=invite.email,
        full_name=full_name or invite.full_name,
        hashed_password=hashed,
        role_id=invite.role_id,
    )
    db.add(user)
    invite.accepted_at = datetime.now(timezone.utc)
    await db.flush()
    result = await db.execute(select(User).options(selectinload(User.role)).where(User.id == user.id))
    return result.scalar_one()
