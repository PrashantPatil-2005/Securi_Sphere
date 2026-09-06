"""Integration tests for agent enrollment and monitoring."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_install_script_served(client: AsyncClient):
    res = await client.get("/install.sh")
    assert res.status_code == 200
    assert "Installing Securi Agent" in res.text
    assert "agent-bundle.tar.gz" in res.text


@pytest.mark.asyncio
async def test_agent_bundle_served(client: AsyncClient):
    res = await client.get("/agent-bundle.tar.gz")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/gzip")
    assert len(res.content) > 100

    import io
    import tarfile


    tmp = io.BytesIO(res.content)
    with tarfile.open(fileobj=tmp, mode="r:gz") as tar:
        names = {m.name.lstrip("./").replace("\\", "/") for m in tar.getmembers() if m.isfile()}
    assert "agent/main.py" in names
    assert "requirements.txt" in names


@pytest.mark.asyncio
async def test_agent_enrollment_flow(admin_client: AsyncClient):
    host_res = await admin_client.post("/api/v1/hosts", json={"name": "test-agent-host"})
    assert host_res.status_code == 200
    host = host_res.json()
    assert host["enrolled"] is False
    assert host["status"] == "inactive"

    token_res = await admin_client.post(f"/api/v1/hosts/{host['id']}/enrollment-token")
    assert token_res.status_code == 200
    token_data = token_res.json()
    assert token_data["token"].startswith("enroll_")
    assert "install.sh" in token_data["install_command"]

    reg_res = await admin_client.post(
        "/api/v1/agent/register",
        json={
            "enrollment_token": token_data["token"],
            "hostname": "vm-test",
            "ip_address": "10.0.0.5",
            "os_info": "Linux 6.1",
        },
    )
    assert reg_res.status_code == 200
    api_key = reg_res.json()["api_key"]
    assert api_key.startswith("sk_live_")

    hb_res = await admin_client.post(
        "/api/v1/agent/heartbeat",
        headers={"X-API-Key": api_key},
        json={"agent_version": "2.0.0"},
    )
    assert hb_res.status_code == 200

    host_res2 = await admin_client.get(f"/api/v1/hosts/{host['id']}")
    assert host_res2.status_code == 200
    updated = host_res2.json()
    assert updated["enrolled"] is True
    assert updated["hostname"] == "vm-test"
    assert updated["last_seen"] is not None


@pytest.mark.asyncio
async def test_unenrolled_host_stays_offline_not_critical(admin_client: AsyncClient):
    """Pending hosts must not be marked critical before agent install."""
    host_res = await admin_client.post("/api/v1/hosts", json={"name": "pending-host"})
    host_id = host_res.json()["id"]

    host_check = await admin_client.get(f"/api/v1/hosts/{host_id}")
    data = host_check.json()
    assert data["status"] == "inactive"
    assert data["enrolled"] is False


@pytest.mark.asyncio
async def test_invalid_api_key_rejected_401(client: AsyncClient):
    """Agent with fabricated API key gets 401."""
    res = await client.post(
        "/api/v1/agent/heartbeat",
        headers={"X-API-Key": "sk_live_fabricated_key"},
        json={"agent_version": "1.0.0"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_consume_token_then_re_register(client: AsyncClient, admin_client: AsyncClient):
    """Consume an enrollment token, register once, then register again with a new token on the same host."""
    host_res = await admin_client.post("/api/v1/hosts", json={"name": "re-register-host"})
    host = host_res.json()

    # First enrollment
    token1_res = await admin_client.post(f"/api/v1/hosts/{host['id']}/enrollment-token")
    token1 = token1_res.json()["token"]
    reg1 = await client.post(
        "/api/v1/agent/register",
        json={
            "enrollment_token": token1,
            "hostname": "re-register-host",
            "ip_address": "10.0.0.99",
            "os_info": "Linux 6.1",
        },
    )
    assert reg1.status_code == 200
    api_key1 = reg1.json()["api_key"]
    assert api_key1.startswith("sk_live_")

    # First API key works
    hb1 = await client.post(
        "/api/v1/agent/heartbeat",
        headers={"X-API-Key": api_key1},
        json={"agent_version": "1.0.0"},
    )
    assert hb1.status_code == 200

    # Second enrollment on same host (simulates re-install with new token)
    token2_res = await admin_client.post(f"/api/v1/hosts/{host['id']}/enrollment-token")
    token2 = token2_res.json()["token"]
    reg2 = await client.post(
        "/api/v1/agent/register",
        json={
            "enrollment_token": token2,
            "hostname": "re-register-host",
            "ip_address": "10.0.0.99",
            "os_info": "Linux 6.2",
        },
    )
    assert reg2.status_code == 200
    api_key2 = reg2.json()["api_key"]
    assert api_key2 != api_key1  # new key issued

    # New key works
    hb2 = await client.post(
        "/api/v1/agent/heartbeat",
        headers={"X-API-Key": api_key2},
        json={"agent_version": "1.0.0"},
    )
    assert hb2.status_code == 200

    # Old key is now rejected (server uses new hash)
    hb_old = await client.post(
        "/api/v1/agent/heartbeat",
        headers={"X-API-Key": api_key1},
        json={"agent_version": "1.0.0"},
    )
    assert hb_old.status_code == 401


@pytest.mark.asyncio
async def test_used_enrollment_token_rejected(client: AsyncClient, admin_client: AsyncClient):
    """An enrollment token that was already used cannot be reused."""
    host_res = await admin_client.post("/api/v1/hosts", json={"name": "token-reuse-host"})
    host = host_res.json()

    token_res = await admin_client.post(f"/api/v1/hosts/{host['id']}/enrollment-token")
    token = token_res.json()["token"]

    # First use — succeeds
    reg1 = await client.post(
        "/api/v1/agent/register",
        json={
            "enrollment_token": token,
            "hostname": "token-reuse-host",
            "ip_address": "10.0.0.10",
            "os_info": "Linux 6.1",
        },
    )
    assert reg1.status_code == 200

    # Second use — token consumed, should fail
    reg2 = await client.post(
        "/api/v1/agent/register",
        json={
            "enrollment_token": token,
            "hostname": "token-reuse-host-v2",
            "ip_address": "10.0.0.11",
            "os_info": "Linux 6.1",
        },
    )
    assert reg2.status_code == 400


@pytest.mark.asyncio
async def test_heartbeat_counts_as_credential_validation(client: AsyncClient, admin_client: AsyncClient):
    """Heartbeat with valid API key returns 200 (used by installer to validate credentials)."""
    host_res = await admin_client.post("/api/v1/hosts", json={"name": "cred-test-host"})
    host = host_res.json()

    token_res = await admin_client.post(f"/api/v1/hosts/{host['id']}/enrollment-token")
    token = token_res.json()["token"]

    reg = await client.post(
        "/api/v1/agent/register",
        json={
            "enrollment_token": token,
            "hostname": "cred-test-host",
            "ip_address": "10.0.0.12",
            "os_info": "Linux 6.1",
        },
    )
    api_key = reg.json()["api_key"]

    # Valid key → 200
    hb = await client.post(
        "/api/v1/agent/heartbeat",
        headers={"X-API-Key": api_key},
        json={"agent_version": "1.0.0"},
    )
    assert hb.status_code == 200

    # Invalid key → 401
    hb_bad = await client.post(
        "/api/v1/agent/heartbeat",
        headers={"X-API-Key": "sk_live_wrong_key"},
        json={"agent_version": "1.0.0"},
    )
    assert hb_bad.status_code == 401
