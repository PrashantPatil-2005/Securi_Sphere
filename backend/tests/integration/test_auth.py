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
async def test_change_password(admin_client: AsyncClient):
    res = await admin_client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "testpass123", "new_password": "newpass456"},
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
        json={"email": "admin@test.local", "password": "newpass456"},
    )
    assert ok.status_code == 200

    # Restore password for other tests in the same session DB
    await admin_client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "newpass456", "new_password": "testpass123"},
    )
