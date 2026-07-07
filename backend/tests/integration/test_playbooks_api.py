"""Integration tests for playbooks API."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_playbook_crud(admin_client: AsyncClient):
    create = await admin_client.post(
        "/api/v1/playbooks",
        json={
            "name": "ci_alert_webhook",
            "trigger_event": "alert_created",
            "min_severity": "high",
            "webhook_url": "https://example.com/hooks/test",
            "webhook_secret": "test-secret",
        },
    )
    assert create.status_code == 201, create.text
    body = create.json()
    playbook_id = body["id"]
    assert body["has_secret"] is True

    listed = await admin_client.get("/api/v1/playbooks")
    assert listed.status_code == 200
    assert any(p["id"] == playbook_id for p in listed.json())

    with patch("app.services.playbooks.httpx.AsyncClient") as mock_client_cls:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = "ok"
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        test = await admin_client.post(f"/api/v1/playbooks/{playbook_id}/test")
        assert test.status_code == 200
        assert test.json()["status"] == "success"

    runs = await admin_client.get(f"/api/v1/playbooks/{playbook_id}/runs")
    assert runs.status_code == 200
    assert len(runs.json()) >= 1

    deleted = await admin_client.delete(f"/api/v1/playbooks/{playbook_id}")
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_viewer_cannot_create_playbook(viewer_client: AsyncClient):
    res = await viewer_client.post(
        "/api/v1/playbooks",
        json={
            "name": "viewer_blocked",
            "trigger_event": "alert_created",
            "webhook_url": "https://example.com/hook",
        },
    )
    assert res.status_code == 403
