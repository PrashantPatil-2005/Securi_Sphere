"""Issue JWT session cookies after successful authentication."""

from datetime import datetime, timedelta, timezone

from fastapi import Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_cookies import set_auth_cookies
from app.config import settings
from app.dependencies import client_ip
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.models.user_session import UserSession
from app.schemas.auth import TokenResponse
from app.security import create_access_token, create_refresh_token, hash_token


async def issue_auth_tokens(
    db: AsyncSession,
    user: User,
    request: Request,
    response: Response,
) -> TokenResponse:
    now = datetime.now(timezone.utc)
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
