"""Integration tests for notification rules API."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_notification_rules_crud(analyst_client: AsyncClient):
    create = await analyst_client.post(
        "/api/v1/notifications/rules",
        json={
            "name": "High alerts email",
            "trigger_event": "alert_created",
            "min_severity": "high",
            "channels": {"email": True, "slack": False, "telegram": False},
        },
    )
    assert create.status_code == 201, create.text
    rule_id = create.json()["id"]

    listed = await analyst_client.get("/api/v1/notifications/rules")
    assert listed.status_code == 200
    assert any(r["id"] == rule_id for r in listed.json())

    patch = await analyst_client.patch(
        f"/api/v1/notifications/rules/{rule_id}",
        json={"enabled": False},
    )
    assert patch.status_code == 200
    assert patch.json()["enabled"] is False

    deleted = await analyst_client.delete(f"/api/v1/notifications/rules/{rule_id}")
    assert deleted.status_code == 204
