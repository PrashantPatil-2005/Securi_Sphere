"""OpenID Connect login routes."""

from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import client_ip
from app.services.audit import log_audit
from app.services.auth_session import issue_auth_tokens
from app.services.oidc import (
    build_authorization_url,
    complete_oidc_login,
    create_login_state,
    get_discovery,
    oidc_configured,
    safe_next_path,
)

router = APIRouter(prefix="/auth/oidc", tags=["auth"])


@router.get("/login")
async def oidc_login(next: str | None = Query(None)):
    if not oidc_configured():
        raise HTTPException(status_code=404, detail="OIDC is not enabled")

    discovery = await get_discovery()
    state, nonce = create_login_state(safe_next_path(next))
    url = build_authorization_url(discovery, state, nonce)
    return RedirectResponse(url=url, status_code=302)


@router.get("/callback")
async def oidc_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    if not oidc_configured():
        raise HTTPException(status_code=404, detail="OIDC is not enabled")

    frontend = settings.frontend_url.rstrip("/")
    if error:
        return RedirectResponse(
            url=f"{frontend}/login?error={quote(error)}",
            status_code=302,
        )
    if not code or not state:
        return RedirectResponse(
            url=f"{frontend}/login?error={quote('missing_code')}",
            status_code=302,
        )

    try:
        user, next_path = await complete_oidc_login(db, code, state)
    except HTTPException as exc:
        return RedirectResponse(
            url=f"{frontend}/login?error={quote(str(exc.detail))}",
            status_code=302,
        )
    except Exception:
        return RedirectResponse(
            url=f"{frontend}/login?error={quote('oidc_failed')}",
            status_code=302,
        )

    user.last_login = datetime.now(timezone.utc)
    await log_audit(db, "oidc_login", user_id=user.id, ip_address=client_ip(request))
    redirect = RedirectResponse(url=f"{frontend}{next_path}", status_code=302)
    await issue_auth_tokens(db, user, request, redirect)
    await db.commit()
    return redirect
