"""Integration tests for maintenance windows API."""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from tests.integration.helpers import enroll_test_host


@pytest.mark.asyncio
async def test_maintenance_window_crud(analyst_client: AsyncClient):
    host_id, _ = await enroll_test_host(analyst_client, "maint-api-host")
    ends = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

    create = await analyst_client.post(
        "/api/v1/maintenance-windows",
        json={"host_id": host_id, "reason": "Patch window", "ends_at": ends},
    )
    assert create.status_code == 200
    window_id = create.json()["id"]

    listing = await analyst_client.get("/api/v1/maintenance-windows")
    assert listing.status_code == 200
    assert any(w["id"] == window_id for w in listing.json())

    delete = await analyst_client.delete(f"/api/v1/maintenance-windows/{window_id}")
    assert delete.status_code == 200
