"""Issue JWT session cookies after successful authentication."""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import Request, Response
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_cookies import set_auth_cookies
from app.config import settings
from app.dependencies import client_ip
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.models.user_session import UserSession
from app.schemas.auth import TokenResponse
from app.security import create_access_token, create_refresh_token, hash_token

logger = logging.getLogger(__name__)


async def issue_auth_tokens(
    db: AsyncSession,
    user: User,
    request: Request,
    response: Response,
) -> TokenResponse:
    now = datetime.now(timezone.utc)

    # Enforce concurrent session limit — revoke oldest excess sessions
    session_count = (
        await db.execute(
            select(func.count()).select_from(UserSession).where(
                UserSession.user_id == user.id,
                UserSession.revoked_at.is_(None),
            )
        )
    ).scalar_one()
    if session_count >= settings.max_concurrent_sessions:
        excess = session_count - settings.max_concurrent_sessions + 1
        oldest = (
            await db.execute(
                select(UserSession)
                .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
                .order_by(UserSession.created_at.asc())
                .limit(excess)
            )
        ).scalars().all()
        for sess in oldest:
            sess.revoked_at = now
            # Also revoke associated refresh token
            if sess.refresh_token_hash:
                await db.execute(
                    select(RefreshToken).where(
                        RefreshToken.token_hash == sess.refresh_token_hash,
                        RefreshToken.revoked_at.is_(None),
                    )
                )
                rt = (await db.execute(
                    select(RefreshToken).where(
                        RefreshToken.token_hash == sess.refresh_token_hash,
                    )
                )).scalar_one_or_none()
                if rt:
                    rt.revoked_at = now
        if oldest:
            logger.info(
                "revoked %d excess sessions for user %s (limit %d)",
                len(oldest), user.id, settings.max_concurrent_sessions,
            )

    access = create_access_token(str(user.id), user.role.name)
    refresh = create_refresh_token(str(user.id))
    refresh_hash = hash_token(refresh)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=now + timedelta(days=settings.jwt_refresh_expire_days),
            created_at=now,
        )
    )
    db.add(
        UserSession(
            user_id=user.id,
            refresh_token_hash=refresh_hash,
            device_name=request.headers.get("X-Device-Name"),
            ip_address=client_ip(request),
            user_agent=request.headers.get("User-Agent", "")[:512],
            expires_at=now + timedelta(days=settings.jwt_refresh_expire_days),
        )
    )
    set_auth_cookies(response, access, refresh)
    return TokenResponse(access_token=access, refresh_token=refresh)
