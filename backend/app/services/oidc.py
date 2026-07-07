"""OpenID Connect (OIDC) login — Google, Azure AD, and compatible IdPs."""

from __future__ import annotations

import logging
import secrets
import time
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException
from jose import jwk, jwt
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.http_timeouts import outbound_timeout
from app.models.role import Role
from app.models.user import User
from app.services.oidc_roles import email_domain_allowed, resolve_role_from_claims

logger = logging.getLogger(__name__)

_discovery_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_jwks_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_CACHE_TTL = 3600


def oidc_configured() -> bool:
    return bool(
        settings.oidc_enabled
        and settings.oidc_issuer_url
        and settings.oidc_client_id
        and settings.oidc_client_secret
    )


def oidc_redirect_uri() -> str:
    return f"{settings.server_url.rstrip('/')}/api/v1/auth/oidc/callback"


def safe_next_path(path: str | None) -> str:
    if not path or not path.startswith("/") or path.startswith("//"):
        return "/"
    return path


async def _fetch_json(url: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=outbound_timeout(short=True)) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


async def get_discovery() -> dict[str, Any]:
    issuer = settings.oidc_issuer_url.rstrip("/")
    now = time.time()
    cached = _discovery_cache.get(issuer)
    if cached and now - cached[0] < _CACHE_TTL:
        return cached[1]

    doc = await _fetch_json(f"{issuer}/.well-known/openid-configuration")
    _discovery_cache[issuer] = (now, doc)
    return doc


async def get_jwks(jwks_uri: str) -> dict[str, Any]:
    now = time.time()
    cached = _jwks_cache.get(jwks_uri)
    if cached and now - cached[0] < _CACHE_TTL:
        return cached[1]

    doc = await _fetch_json(jwks_uri)
    _jwks_cache[jwks_uri] = (now, doc)
    return doc


def build_authorization_url(discovery: dict[str, Any], state: str, nonce: str) -> str:
    params = {
        "client_id": settings.oidc_client_id,
        "response_type": "code",
        "scope": settings.oidc_scopes,
        "redirect_uri": oidc_redirect_uri(),
        "state": state,
        "nonce": nonce,
    }
    return f"{discovery['authorization_endpoint']}?{urlencode(params)}"


async def exchange_code(discovery: dict[str, Any], code: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=outbound_timeout(short=True)) as client:
        response = await client.post(
            discovery["token_endpoint"],
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": oidc_redirect_uri(),
                "client_id": settings.oidc_client_id,
                "client_secret": settings.oidc_client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if response.status_code >= 400:
            logger.warning("OIDC token exchange failed: %s", response.text[:500])
            raise HTTPException(status_code=401, detail="OIDC token exchange failed")
        return response.json()


def verify_id_token(
    id_token: str,
    jwks: dict[str, Any],
    *,
    audience: str,
    issuer: str,
    nonce: str,
) -> dict[str, Any]:
    header = jwt.get_unverified_header(id_token)
    kid = header.get("kid")
    key_data = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if not key_data:
        raise HTTPException(status_code=401, detail="OIDC signing key not found")

    key = jwk.construct(key_data)
    algorithms = [header.get("alg") or "RS256"]
    claims = jwt.decode(
        id_token,
        key,
        algorithms=algorithms,
        audience=audience,
        issuer=issuer,
        options={"verify_at_hash": False},
    )
    if claims.get("nonce") != nonce:
        raise HTTPException(status_code=401, detail="OIDC nonce mismatch")
    return claims


def create_login_state(next_path: str) -> tuple[str, str]:
    nonce = secrets.token_urlsafe(16)
    state = create_oidc_state_token(next_path=next_path, nonce=nonce)
    return state, nonce


def parse_login_state(state: str) -> tuple[str, str]:
    try:
        payload = decode_oidc_state_token(state)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid OIDC state") from exc
    return payload.get("next", "/"), payload["nonce"]


async def _apply_role_from_claims(db: AsyncSession, user: User, claims: dict[str, Any]) -> User:
    if not settings.oidc_sync_roles_on_login:
        return user
    role_map = (settings.oidc_role_map or "").strip()
    if not role_map:
        return user

    role_name = resolve_role_from_claims(claims)
    if user.role and user.role.name == role_name:
        return user

    role = (
        await db.execute(select(Role).where(Role.name == role_name))
    ).scalar_one_or_none()
    if not role:
        return user
    user.role_id = role.id
    await db.flush()
    result = await db.execute(select(User).options(selectinload(User.role)).where(User.id == user.id))
    return result.scalar_one()


async def resolve_user_from_claims(db: AsyncSession, claims: dict[str, Any]) -> User:
    issuer = settings.oidc_issuer_url.rstrip("/")
    token_issuer = str(claims.get("iss", "")).rstrip("/")
    if token_issuer != issuer:
        raise HTTPException(status_code=401, detail="OIDC issuer mismatch")

    sub = claims.get("sub")
    email = (claims.get("email") or "").strip().lower()
    if not sub:
        raise HTTPException(status_code=401, detail="OIDC subject missing")
    if not email:
        raise HTTPException(status_code=401, detail="OIDC email claim required")

    full_name = claims.get("name") or claims.get("preferred_username")

    by_oidc = (
        await db.execute(
            select(User)
            .options(selectinload(User.role))
            .where(User.oidc_issuer == issuer, User.oidc_sub == sub)
        )
    ).scalar_one_or_none()
    if by_oidc:
        if not by_oidc.is_active:
            raise HTTPException(status_code=403, detail="Account disabled")
        return await _apply_role_from_claims(db, by_oidc, claims)

    by_email = (
        await db.execute(select(User).options(selectinload(User.role)).where(User.email == email))
    ).scalar_one_or_none()
    if by_email:
        if by_email.oidc_sub and by_email.oidc_sub != sub:
            raise HTTPException(status_code=403, detail="Email already linked to another identity")
        by_email.oidc_sub = sub
        by_email.oidc_issuer = issuer
        if full_name and not by_email.full_name:
            by_email.full_name = full_name
        if not by_email.is_active:
            raise HTTPException(status_code=403, detail="Account disabled")
        return await _apply_role_from_claims(db, by_email, claims)

    if not settings.oidc_auto_provision:
        raise HTTPException(status_code=403, detail="User not provisioned for SSO")

    if not email_domain_allowed(email):
        raise HTTPException(status_code=403, detail="Email domain not allowed for SSO")

    count = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    role_name = "admin" if count == 0 else resolve_role_from_claims(claims)
    role = (
        await db.execute(select(Role).where(Role.name == role_name))
    ).scalar_one_or_none()
    if not role:
        role = (await db.execute(select(Role).where(Role.name == "analyst"))).scalar_one()

    user = User(
        email=email,
        full_name=full_name,
        hashed_password=None,
        role_id=role.id,
        oidc_sub=sub,
        oidc_issuer=issuer,
    )
    db.add(user)
    await db.flush()
    result = await db.execute(select(User).options(selectinload(User.role)).where(User.id == user.id))
    return result.scalar_one()


async def complete_oidc_login(db: AsyncSession, code: str, state: str) -> tuple[User, str]:
    next_path, nonce = parse_login_state(state)
    discovery = await get_discovery()
    token_data = await exchange_code(discovery, code)
    id_token = token_data.get("id_token")
    if not id_token:
        raise HTTPException(status_code=401, detail="OIDC id_token missing")

    jwks = await get_jwks(discovery["jwks_uri"])
    issuer = discovery.get("issuer", settings.oidc_issuer_url.rstrip("/"))
    claims = verify_id_token(
        id_token,
        jwks,
        audience=settings.oidc_client_id,
        issuer=issuer,
        nonce=nonce,
    )
    user = await resolve_user_from_claims(db, claims)
    return user, next_path
