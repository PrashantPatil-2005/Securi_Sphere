"""Integration tests for admin user provisioning."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_provision_sso_user(admin_client: AsyncClient):
    res = await admin_client.post(
        "/api/v1/users",
        json={
            "email": "sso-provision-unique@test.local",
            "role": "analyst",
            "full_name": "SSO New",
            "sso_only": True,
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["email"] == "sso-provision-unique@test.local"
    assert body["sso_only"] is True
    assert body["role"]["name"] == "analyst"


@pytest.mark.asyncio
async def test_analyst_cannot_list_users(analyst_client: AsyncClient):
    res = await analyst_client.get("/api/v1/users")
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_invite_and_accept_flow(admin_client: AsyncClient, client: AsyncClient):
    create = await admin_client.post(
        "/api/v1/users/invites",
        json={"email": "invited@test.local", "role": "viewer", "full_name": "Invited User"},
    )
    assert create.status_code == 201
    invite = create.json()
    assert invite["invite_url"]
    token = invite["invite_url"].split("token=")[-1]

    preview = await client.get(f"/api/v1/users/invites/preview?token={token}")
    assert preview.status_code == 200
    assert preview.json()["email"] == "invited@test.local"

    accept = await client.post(
        "/api/v1/users/invites/accept",
        json={"token": token, "password": "invitepass123"},
    )
    assert accept.status_code == 200
    assert accept.json()["email"] == "invited@test.local"

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "invited@test.local", "password": "invitepass123"},
    )
    assert login.status_code == 200
