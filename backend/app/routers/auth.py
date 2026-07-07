from datetime import datetime, timedelta, timezone

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth_cookies import clear_auth_cookies
from app.services.auth_session import issue_auth_tokens
from app.config import settings
from app.database import get_db
from app.dependencies import client_ip, get_current_user
from app.models.password_reset import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.models.role import Role
from app.models.user import User
from app.models.user_session import UserSession
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    MfaDisableRequest,
    MfaEnableRequest,
    MfaEnableResponse,
    MfaSetupResponse,
    MfaStatusResponse,
    MfaVerifyRequest,
    ProfileUpdateRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
from app.security import (
    create_mfa_pending_token,
    decode_mfa_pending_token,
    decode_token,
    generate_reset_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.services.mfa import (
    generate_backup_codes,
    generate_totp_secret,
    hash_backup_codes,
    totp_provisioning_uri,
    verify_backup_code,
    verify_totp,
)
from app.services.audit import log_audit
from app.services.notifications import send_email
from app.services.recovery_rate_limit import (
    check_forgot_password,
    check_mfa_verify,
    check_reset_password,
    record_reset_token_failure,
)

router = APIRouter(prefix="/auth", tags=["auth"])

ROLE_PERMISSIONS = {
    "admin": {"users": "write", "hosts": "write", "alerts": "resolve", "notifications": "write"},
    "analyst": {"users": "read", "hosts": "write", "alerts": "resolve", "notifications": "read"},
    "viewer": {"users": "read", "hosts": "read", "alerts": "read", "notifications": "read"},
}

DEV_USERS = {
    "admin@test.local": "admin",
    "analyst@test.local": "analyst",
    "viewer@test.local": "viewer",
}
DEV_USER_PASSWORD = "testpass123"

DEMO_USER_EMAIL = "demo@securi.local"
DEMO_USER_PASSWORD = "Demo1234!"


async def seed_roles(db: AsyncSession) -> None:
    result = await db.execute(select(func.count()).select_from(Role))
    if result.scalar_one() > 0:
        return
    for name, perms in ROLE_PERMISSIONS.items():
        db.add(Role(name=name, description=f"{name.capitalize()} role", permissions=perms))


async def seed_dev_users(db: AsyncSession) -> None:
    if settings.testing or settings.environment != "development":
        return
    roles = {r.name: r for r in (await db.execute(select(Role))).scalars().all()}
    if not roles:
        return
    for email, role_name in DEV_USERS.items():
        role = roles.get(role_name)
        if not role:
            continue
        existing = (
            await db.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        if existing:
            existing.hashed_password = hash_password(DEV_USER_PASSWORD)
            existing.role_id = role.id
            existing.is_active = True
            existing.failed_login_attempts = 0
            existing.locked_until = None
        else:
            db.add(
                User(
                    email=email,
                    hashed_password=hash_password(DEV_USER_PASSWORD),
                    role_id=role.id,
                    full_name=role_name.capitalize(),
                )
            )


async def seed_demo_users(db: AsyncSession) -> None:
    """Seed pilot demo admin when DEMO_MODE=true (any environment)."""
    if not settings.demo_mode or settings.testing:
        return
    roles = {r.name: r for r in (await db.execute(select(Role))).scalars().all()}
    admin = roles.get("admin")
    if not admin:
        return
    existing = (
        await db.execute(select(User).where(User.email == DEMO_USER_EMAIL))
    ).scalar_one_or_none()
    if existing:
        existing.hashed_password = hash_password(DEMO_USER_PASSWORD)
        existing.role_id = admin.id
        existing.is_active = True
        existing.full_name = existing.full_name or "Demo Admin"
        existing.failed_login_attempts = 0
        existing.locked_until = None
    else:
        db.add(
            User(
                email=DEMO_USER_EMAIL,
                hashed_password=hash_password(DEMO_USER_PASSWORD),
                role_id=admin.id,
                full_name="Demo Admin",
            )
        )


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

    role_name = "admin" if is_first_user else "analyst"
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


@router.post("/login", response_model=LoginResponse)
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

    if not user or not user.hashed_password or not verify_password(body.password, user.hashed_password):
        if user:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.account_lockout_attempts:
                user.locked_until = now + timedelta(minutes=settings.account_lockout_minutes)
                user.failed_login_attempts = 0
        await log_audit(db, "failed_login", ip_address=client_ip(request), details={"email": body.email})
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user.failed_login_attempts = 0
    user.locked_until = None

    if user.mfa_enabled and user.mfa_secret:
        mfa_token = create_mfa_pending_token(str(user.id))
        await log_audit(db, "mfa_challenge", user_id=user.id, ip_address=client_ip(request))
        return LoginResponse(mfa_required=True, mfa_token=mfa_token)

    user.last_login = now
    await log_audit(db, "login", user_id=user.id, ip_address=client_ip(request))
    tokens = await issue_auth_tokens(db, user, request, response)
    return LoginResponse(access_token=tokens.access_token, refresh_token=tokens.refresh_token)


@router.post("/mfa/verify", response_model=TokenResponse)
async def verify_mfa_login(
    body: MfaVerifyRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    await check_mfa_verify(client_ip(request))
    try:
        payload = decode_mfa_pending_token(body.mfa_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired MFA session")

    user_id = payload.get("sub")
    try:
        uid = UUID(str(user_id))
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid MFA session")
    result = await db.execute(
        select(User).options(selectinload(User.role)).where(User.id == uid)
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active or not user.mfa_enabled or not user.mfa_secret:
        raise HTTPException(status_code=401, detail="MFA not configured")

    ok = verify_totp(user.mfa_secret, body.code)
    backup_used = False
    if not ok:
        matched, remaining = verify_backup_code(user.mfa_backup_codes or [], body.code)
        if matched:
            user.mfa_backup_codes = remaining
            backup_used = True
            ok = True
    if not ok:
        await log_audit(db, "mfa_failed", user_id=user.id, ip_address=client_ip(request))
        raise HTTPException(status_code=401, detail="Invalid authentication code")

    user.last_login = datetime.now(timezone.utc)
    await log_audit(
        db,
        "login",
        user_id=user.id,
        ip_address=client_ip(request),
        details={"mfa": True, "backup_code": backup_used},
    )
    return await issue_auth_tokens(db, user, request, response)


@router.get("/mfa/status", response_model=MfaStatusResponse)
async def mfa_status(user: User = Depends(get_current_user)):
    return MfaStatusResponse(
        enabled=bool(user.mfa_enabled),
        backup_codes_remaining=len(user.mfa_backup_codes or []),
    )


@router.post("/mfa/setup", response_model=MfaSetupResponse)
async def mfa_setup(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA is already enabled")
    secret = generate_totp_secret()
    user.mfa_pending_secret = secret
    await db.flush()
    return MfaSetupResponse(secret=secret, otpauth_url=totp_provisioning_uri(secret, user.email))


@router.post("/mfa/enable", response_model=MfaEnableResponse)
async def mfa_enable(
    body: MfaEnableRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA is already enabled")
    if not user.mfa_pending_secret:
        raise HTTPException(status_code=400, detail="Run MFA setup first")
    if not verify_totp(user.mfa_pending_secret, body.code):
        raise HTTPException(status_code=400, detail="Invalid authentication code")
    plain_codes = generate_backup_codes()
    user.mfa_secret = user.mfa_pending_secret
    user.mfa_pending_secret = None
    user.mfa_enabled = True
    user.mfa_backup_codes = hash_backup_codes(plain_codes)
    await log_audit(db, "mfa_enabled", user_id=user.id, ip_address=client_ip(request))
    return MfaEnableResponse(enabled=True, backup_codes=plain_codes)


@router.post("/mfa/disable")
async def mfa_disable(
    body: MfaDisableRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user.mfa_enabled or not user.mfa_secret:
        raise HTTPException(status_code=400, detail="MFA is not enabled")
    if user.hashed_password:
        if not body.password or not verify_password(body.password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Password is incorrect")
    ok = verify_totp(user.mfa_secret, body.code)
    if not ok:
        matched, _ = verify_backup_code(user.mfa_backup_codes or [], body.code)
        ok = matched
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid authentication code")
    user.mfa_enabled = False
    user.mfa_secret = None
    user.mfa_pending_secret = None
    user.mfa_backup_codes = []
    await log_audit(db, "mfa_disabled", user_id=user.id, ip_address=client_ip(request))
    return {"ok": True}


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
    return await issue_auth_tokens(db, user, request, response)


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
async def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await check_forgot_password(client_ip(request), body.email)
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
    await log_audit(db, "password_reset_requested", user_id=user.id, ip_address=client_ip(request))
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await check_reset_password(client_ip(request))
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
        await record_reset_token_failure(body.token)
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


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user.hashed_password:
        raise HTTPException(status_code=400, detail="SSO account — change password via your identity provider")
    if not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if body.current_password == body.new_password:
        raise HTTPException(status_code=400, detail="New password must differ from current password")
    user.hashed_password = hash_password(body.new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    await log_audit(db, "password_change", user_id=user.id, ip_address=client_ip(request))
    return {"message": "Password updated"}
