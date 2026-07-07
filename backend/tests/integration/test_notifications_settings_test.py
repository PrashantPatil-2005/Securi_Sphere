"""Integration tests for notification delivery settings test endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_delivery_settings_test_requires_channels(analyst_client: AsyncClient):
    res = await analyst_client.post(
        "/api/v1/notifications/settings/test",
        json={
            "channels": {"email": False, "slack": False, "telegram": False},
            "email_enabled": False,
            "slack_enabled": False,
            "telegram_enabled": False,
        },
    )
    assert res.status_code == 400
    body = res.json()
    message = body.get("detail") or body.get("error", {}).get("message", "")
    assert "No channels delivered" in message


@pytest.mark.asyncio
async def test_delivery_settings_test_without_address(analyst_client: AsyncClient):
    res = await analyst_client.post(
        "/api/v1/notifications/settings/test",
        json={
            "channels": {"email": True, "slack": False, "telegram": False},
            "email_enabled": True,
            "email_address": "",
        },
    )
    assert res.status_code == 400
