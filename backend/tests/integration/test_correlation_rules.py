"""HTTP integration tests for correlation rule CRUD."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_viewer_cannot_create_correlation_rule(viewer_client: AsyncClient):
    res = await viewer_client.post(
        "/api/v1/correlation-rules",
        json={
            "name": "Viewer Rule",
            "rule_type": "sequence",
            "event_sequence": ["ssh_login_failure"],
        },
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_admin_correlation_rule_crud(admin_client: AsyncClient):
    create = await admin_client.post(
        "/api/v1/correlation-rules",
        json={
            "name": "Integration Custom Sequence",
            "description": "Test custom correlation",
            "rule_type": "sequence",
            "event_sequence": ["ssh_login_failure", "sudo_usage"],
            "window_minutes": 15,
            "min_occurrences": {"ssh_login_failure": 2},
            "severity": "high",
        },
    )
    assert create.status_code == 200, create.text
    body = create.json()
    rule_id = body["id"]
    assert body["is_system"] is False
    assert body["rule_type"] == "sequence"
    assert body["enabled"] is True

    listed = await admin_client.get("/api/v1/correlation-rules")
    assert listed.status_code == 200
    assert any(r["id"] == rule_id for r in listed.json())

    patched = await admin_client.patch(
        f"/api/v1/correlation-rules/{rule_id}",
        json={"enabled": False, "severity": "critical"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["enabled"] is False
    assert patched.json()["severity"] == "critical"

    deleted = await admin_client.delete(f"/api/v1/correlation-rules/{rule_id}")
    assert deleted.status_code == 200, deleted.text

    listed_after = await admin_client.get("/api/v1/correlation-rules")
    assert not any(r["id"] == rule_id for r in listed_after.json())


@pytest.mark.asyncio
async def test_system_correlation_rule_cannot_be_deleted(admin_client: AsyncClient):
    listed = await admin_client.get("/api/v1/correlation-rules")
    assert listed.status_code == 200
    system_rule = next((r for r in listed.json() if r.get("is_system")), None)
    if not system_rule:
        pytest.skip("No seeded system correlation rules")

    res = await admin_client.delete(f"/api/v1/correlation-rules/{system_rule['id']}")
    assert res.status_code == 400

    toggle = await admin_client.patch(
        f"/api/v1/correlation-rules/{system_rule['id']}",
        json={"enabled": not system_rule["enabled"]},
    )
    assert toggle.status_code == 200, toggle.text
