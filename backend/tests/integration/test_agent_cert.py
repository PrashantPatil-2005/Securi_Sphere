"""Integration tests for agent mTLS certificate fingerprint registration."""

import pytest
from httpx import AsyncClient

SAMPLE_FINGERPRINT = "a" * 64


@pytest.mark.asyncio
async def test_register_agent_cert(admin_client: AsyncClient):
    host_res = await admin_client.post("/api/v1/hosts", json={"name": "mtls-host"})
    assert host_res.status_code == 200
    host_id = host_res.json()["id"]

    cert_res = await admin_client.post(
        f"/api/v1/hosts/{host_id}/agent-cert",
        json={"cert_fingerprint": SAMPLE_FINGERPRINT},
    )
    assert cert_res.status_code == 200, cert_res.text
    body = cert_res.json()
    assert body["ok"] is True
    assert body["agent_cert_fingerprint"] == SAMPLE_FINGERPRINT


@pytest.mark.asyncio
async def test_enrollment_token_includes_mtls_note_when_enabled(monkeypatch, admin_client: AsyncClient):
    from app.config import settings

    monkeypatch.setattr(settings, "agent_mtls_enabled", True)
    host_res = await admin_client.post("/api/v1/hosts", json={"name": "mtls-note-host"})
    host_id = host_res.json()["id"]

    token_res = await admin_client.post(f"/api/v1/hosts/{host_id}/enrollment-token")
    assert token_res.status_code == 200
    data = token_res.json()
    assert data["mtls_note"]
    assert "agent-cert" in data["mtls_note"]


@pytest.mark.asyncio
async def test_register_agent_cert_requires_analyst_or_admin(viewer_client: AsyncClient, admin_client: AsyncClient):
    host_res = await admin_client.post("/api/v1/hosts", json={"name": "rbac-host"})
    host_id = host_res.json()["id"]

    denied = await viewer_client.post(
        f"/api/v1/hosts/{host_id}/agent-cert",
        json={"cert_fingerprint": SAMPLE_FINGERPRINT},
    )
    assert denied.status_code == 403
