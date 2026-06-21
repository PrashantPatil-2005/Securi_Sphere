"""HttpOnly cookie helpers for JWT auth."""

from datetime import timedelta

from fastapi import Response

from app.config import settings

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"


def _cookie_secure() -> bool:
    return settings.environment != "development"


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access_token,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        max_age=int(timedelta(minutes=settings.jwt_access_expire_minutes).total_seconds()),
        path="/",
    )
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        max_age=int(timedelta(days=settings.jwt_refresh_expire_days).total_seconds()),
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/")
