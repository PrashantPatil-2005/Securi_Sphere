from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth_cookies import clear_auth_cookies, set_auth_cookies
from app.config import settings
from app.database import get_db
from app.dependencies import client_ip, get_current_user
from app.models.password_reset import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.models.role import Role
from app.models.user import User
from app.models.user_session import UserSession
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    ProfileUpdateRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_reset_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.services.audit import log_audit
from app.services.notifications import send_email

router = APIRouter(prefix="/auth", tags=["auth"])

ROLE_PERMISSIONS = {
    "admin": {"users": "write", "hosts": "write", "alerts": "resolve", "notifications": "write"},
    "analyst": {"users": "read", "hosts": "write", "alerts": "resolve", "notifications": "read"},
    "viewer": {"users": "read", "hosts": "read", "alerts": "read", "notifications": "read"},
}


async def seed_roles(db: AsyncSession) -> None:
    result = await db.execute(select(func.count()).select_from(Role))
    if result.scalar_one() > 0:
        return
    for name, perms in ROLE_PERMISSIONS.items():
        db.add(Role(name=name, description=f"{name.capitalize()} role", permissions=perms))


async def _issue_tokens(
    db: AsyncSession,
    user: User,
    request: Request,
    response: Response,
) -> TokenResponse:
    now = datetime.now(timezone.utc)
    access = create_access_token(str(user.id), user.role.name)
    refresh = create_refresh_token(str(user.id))
    refresh_hash = hash_token(refresh)
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=refresh_hash,
        expires_at=now + timedelta(days=settings.jwt_refresh_expire_days),
        created_at=now,
    ))
    db.add(UserSession(
        user_id=user.id,
        refresh_token_hash=refresh_hash,
        device_name=request.headers.get("X-Device-Name"),
        ip_address=client_ip(request),
        user_agent=request.headers.get("User-Agent", "")[:512],
        expires_at=now + timedelta(days=settings.jwt_refresh_expire_days),
    ))
    set_auth_cookies(response, access, refresh)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/register", response_model=UserResponse)
async def register(body: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    await seed_roles(db)
    count = await db.execute(select(func.count()).select_from(User))
    is_first_user = count.scalar_one() == 0
    if not is_first_user and not settings.allow_registration:
        raise HTTPException(status_code=403, detail="Registration is disabled")

    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    role_name = "admin" if is_first_user else "viewer"
    role_result = await db.execute(select(Role).where(Role.name == role_name))
    role = role_result.scalar_one()

    user = User(email=body.email, hashed_password=hash_password(body.password), role_id=role.id)
    db.add(user)
    await db.flush()
    await log_audit(db, "register", user_id=user.id, ip_address=client_ip(request))
    result = await db.execute(
        select(User).options(selectinload(User.role)).where(User.id == user.id)
    )
    return result.scalar_one()


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).options(selectinload(User.role)).where(User.email == body.email)
    )
    user = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if user and user.locked_until and user.locked_until > now:
        raise HTTPException(
            status_code=429,
            detail=f"Account locked until {user.locked_until.isoformat()}",
        )

    if not user or not verify_password(body.password, user.hashed_password):
        if user:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.account_lockout_attempts:
                user.locked_until = now + timedelta(minutes=settings.account_lockout_minutes)
                user.failed_login_attempts = 0
        await log_audit(db, "failed_login", ip_address=client_ip(request), details={"email": body.email})
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = now
    await log_audit(db, "login", user_id=user.id, ip_address=client_ip(request))
    return await _issue_tokens(db, user, request, response)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    body: RefreshRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    refresh_token = (body.refresh_token if body else None) or request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token required")

    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    token_hash = hash_token(refresh_token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
    )
    stored = result.scalar_one_or_none()
    if not stored:
        raise HTTPException(status_code=401, detail="Refresh token expired or revoked")

    session = (
        await db.execute(
            select(UserSession).where(
                UserSession.refresh_token_hash == token_hash,
                UserSession.revoked_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=401, detail="Session revoked")

    user_result = await db.execute(
        select(User).options(selectinload(User.role)).where(User.id == stored.user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    await db.delete(stored)
    session.revoked_at = datetime.now(timezone.utc)
    return await _issue_tokens(db, user, request, response)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    body: LogoutRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    refresh_token = (body.refresh_token if body else None) or request.cookies.get("refresh_token")
    user_id = None
    if refresh_token:
        token_hash = hash_token(refresh_token)
        stored = (
            await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        ).scalar_one_or_none()
        if stored:
            user_id = stored.user_id
        await db.execute(delete(RefreshToken).where(RefreshToken.token_hash == token_hash))
        session = (
            await db.execute(
                select(UserSession).where(
                    UserSession.refresh_token_hash == token_hash,
                    UserSession.revoked_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if session:
            session.revoked_at = datetime.now(timezone.utc)
    clear_auth_cookies(response)
    if user_id:
        await log_audit(db, "logout", user_id=user_id, ip_address=client_ip(request))
    return {"message": "Logged out"}


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user:
        return {"message": "If the email exists, a reset link has been sent"}

    token = generate_reset_token()
    db.add(PasswordResetToken(
        user_id=user.id,
        token_hash=hash_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    ))
    reset_url = f"{settings.frontend_url}/reset-password?token={token}"
    await send_email(user.email, "Password Reset", f"<p>Reset your password: <a href='{reset_url}'>{reset_url}</a></p>")
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    token_hash = hash_token(body.token)
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > datetime.now(timezone.utc),
        )
    )
    reset_token = result.scalar_one_or_none()
    if not reset_token:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user_result = await db.execute(select(User).where(User.id == reset_token.user_id))
    user = user_result.scalar_one()
    user.hashed_password = hash_password(body.new_password)
    reset_token.used_at = datetime.now(timezone.utc)
    await log_audit(db, "password_reset", user_id=user.id)
    return {"message": "Password reset successful"}


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: ProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if body.full_name is not None:
        user.full_name = body.full_name.strip() or None
    await db.flush()
    result = await db.execute(
        select(User).options(selectinload(User.role)).where(User.id == user.id)
    )
    return result.scalar_one()
