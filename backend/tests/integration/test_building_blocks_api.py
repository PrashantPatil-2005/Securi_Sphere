"""Integration tests for building blocks API."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_building_block_crud(admin_client: AsyncClient):
    create = await admin_client.post(
        "/api/v1/building-blocks",
        json={
            "name": "test_block_crud",
            "description": "test",
            "category": "auth",
            "siem_query": "event_type:failed_login date:24h",
        },
    )
    assert create.status_code == 201
    block_id = create.json()["id"]

    listing = await admin_client.get("/api/v1/building-blocks")
    assert listing.status_code == 200
    assert any(b["id"] == block_id for b in listing.json())

    update = await admin_client.patch(
        f"/api/v1/building-blocks/{block_id}",
        json={"enabled": False, "siem_query": "event_type:ssh_login_failure date:24h"},
    )
    assert update.status_code == 200
    assert update.json()["enabled"] is False

    delete = await admin_client.delete(f"/api/v1/building-blocks/{block_id}")
    assert delete.status_code == 204
