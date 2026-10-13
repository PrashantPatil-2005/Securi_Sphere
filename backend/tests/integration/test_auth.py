"""HTTP integration tests for authentication."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_sets_cookies_and_me(client: AsyncClient):
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.local", "password": "testpass123"},
    )
    assert res.status_code == 200
    assert "access_token" in res.cookies
    assert "refresh_token" in res.cookies
    body = res.json()
    assert body["access_token"]
    assert body["refresh_token"]

    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "admin@test.local"


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient):
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.local", "password": "wrong-password"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_me_unauthenticated(client: AsyncClient):
    res = await client.get("/api/v1/auth/me")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rotates_session(admin_client: AsyncClient):
    res = await admin_client.post("/api/v1/auth/refresh", json={})
    assert res.status_code == 200
    assert res.json()["access_token"]

    me = await admin_client.get("/api/v1/auth/me")
    assert me.status_code == 200


@pytest.mark.asyncio
async def test_logout_clears_session(admin_client: AsyncClient):
    res = await admin_client.post("/api/v1/auth/logout", json={})
    assert res.status_code == 200

    me = await admin_client.get("/api/v1/auth/me")
    assert me.status_code == 401


@pytest.mark.asyncio
async def test_weak_password_rejected_with_422_not_500(client: AsyncClient):
    """Pydantic value errors must serialize to JSON (they used to 500)."""
    res = await client.post(
        "/api/v1/auth/register",
        json={"email": "weak-pass@test.local", "password": "alllowercase1"},
    )
    assert res.status_code == 422, res.text
    body = res.json()
    assert body["error"]["code"] == "validation_error"
    assert "Password must be at least 8 characters" in str(body["error"]["details"])


@pytest.mark.asyncio
async def test_change_password(admin_client: AsyncClient):
    # Must satisfy the backend password policy (upper/lower/digit/special, 8+).
    res = await admin_client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "testpass123", "new_password": "Newpass!456"},
    )
    assert res.status_code == 200
    assert res.json()["message"] == "Password updated"

    bad = await admin_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.local", "password": "testpass123"},
    )
    assert bad.status_code == 401

    ok = await admin_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.local", "password": "Newpass!456"},
    )
    assert ok.status_code == 200

    # Restore the shared fixture password for other tests in the same session DB.
    # Done via a direct DB write: the API only accepts policy-compliant passwords,
    # and the fixture password "testpass123" intentionally sits below that bar.
    from sqlalchemy import select

    from app.database import async_session
    from app.models.user import User
    from app.security import hash_password

    async with async_session() as db:
        admin = (
            await db.execute(select(User).where(User.email == "admin@test.local"))
        ).scalar_one()
        admin.hashed_password = hash_password("testpass123")
        await db.commit()


@pytest.mark.asyncio
async def test_forgot_and_reset_password_flow(client: AsyncClient, monkeypatch):
    """Full recovery flow: request link -> email carries token -> reset -> login."""
    import re

    from sqlalchemy import delete, select

    from app.database import async_session
    from app.models.password_reset import PasswordResetToken
    from app.models.user import User
    from app.routers import auth as auth_router
    from app.security import hash_password
    from app.services.recovery_rate_limit import reset_memory_buckets

    reset_memory_buckets()

    sent: dict[str, str] = {}

    async def capture_email(to: str, subject: str, body: str) -> bool:
        sent.update(to=to, subject=subject, body=body)
        return True

    monkeypatch.setattr(auth_router, "send_email", capture_email)

    try:
        # Unknown address must look identical to a known one (no enumeration)
        # and must not trigger an email.
        res = await client.post(
            "/api/v1/auth/forgot-password", json={"email": "nobody@test.local"}
        )
        assert res.status_code == 200
        assert res.json() == {"message": "If the email exists, a reset link has been sent"}
        assert not sent

        res = await client.post(
            "/api/v1/auth/forgot-password", json={"email": "admin@test.local"}
        )
        assert res.status_code == 200
        assert sent["to"] == "admin@test.local"
        assert "Password Reset" in sent["subject"]
        match = re.search(r"token=([A-Za-z0-9._-]+)", sent["body"])
        assert match, sent["body"]
        token = match.group(1)

        res = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": "BrandNew!123"},
        )
        assert res.status_code == 200, res.text
        assert res.json()["message"] == "Password reset successful"

        # Token is single-use
        res = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": "Another!123"},
        )
        assert res.status_code == 400

        # Old password dead, new password works
        res = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.local", "password": "testpass123"},
        )
        assert res.status_code == 401
        res = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.local", "password": "BrandNew!123"},
        )
        assert res.status_code == 200, res.text
    finally:
        # Restore shared fixture state for other tests in the same session DB.
        async with async_session() as db:
            admin = (
                await db.execute(select(User).where(User.email == "admin@test.local"))
            ).scalar_one()
            admin.hashed_password = hash_password("testpass123")
            await db.execute(delete(PasswordResetToken))
            await db.commit()
        reset_memory_buckets()
