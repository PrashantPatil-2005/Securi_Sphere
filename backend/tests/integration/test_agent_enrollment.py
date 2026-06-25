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

    from app.utils.agent_bundle import validate_bundle

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
    assert host["status"] == "offline"

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
    assert data["status"] == "offline"
    assert data["enrolled"] is False
